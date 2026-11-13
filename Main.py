"""
main.py - loop principal do piloto autonomo.

Roda: python3 main.py
Sai:  tecla 'q' na janela, ou Ctrl+C

Responsabilidade deste arquivo: SO orquestrar.
Ele nao sabe processar imagem (isso e do vision.py), nao sabe calcular
correcao (controller.py) e nao sabe falar com GPIO (MotorModule.py).
"""

import time
import cv2

import config
from vision import LaneVision
from controller import SteeringPID, speed_for
from MotorModule import Motor
from cone_vision import ConeCamera
from desvio import DesvioCone

DEBUG = False          # desligado = mais FPS = reacao mais rapida


def abrir_camera():
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

    # MJPG e ate 5-10x mais rapido que o formato bruto (YUYV) em USB, porque
    # chega comprimido. Muita webcam barata fica em YUYV por padrao e trava
    # o FPS bem antes do seu codigo entrar em acao - foi exatamente o caso
    # aqui (camera sozinha comendo 117-160ms/frame, visao gastando so 9-18ms).
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_RES[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_RES[1])
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)     # sempre o frame mais novo, nunca atrasado

    # confere se o driver aceitou de verdade (alguns ignoram set() em silencio)
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc_str = "".join([chr((fourcc >> 8*i) & 0xFF) for i in range(4)])
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Camera aberta: {w}x{h} @ {fps:.0f}fps pedido, formato={fourcc_str}")
    if fourcc_str.strip() != "MJPG":
        print("AVISO: a camera NAO aceitou MJPG. E provavel que o gargalo de "
              "captura continue. Rode 'v4l2-ctl --list-formats-ext -d /dev/video0' "
              "pra ver quais formatos ela realmente suporta.")
    return cap


def main():
    print("Piloto autonomo: navegando ENTRE as faixas.")

    cap = abrir_camera()
    if not cap.isOpened():
        print("Erro critico: camera nao abriu.")
        return

    # 2a camera: so cones. Roda numa thread propria (nao pesa no FPS da pista).
    cones = None
    if config.CONE_ATIVO:
        cones = ConeCamera()
        if not cones.start():
            print(f"Erro critico: camera dos cones nao abriu "
                  f"(CONE_CAMERA_INDEX={config.CONE_CAMERA_INDEX}). "
                  f"Rode 'v4l2-ctl --list-devices' ou ponha CONE_ATIVO=False.")
            cap.release()
            return
    desvio = DesvioCone()

    vision = LaneVision()
    pid = SteeringPID()
    motor = Motor(config.ENA_A, config.IN1_A, config.IN2_A,
                  config.ENA_B, config.IN3_B, config.IN4_B,
                  config.SERVO_PIN)

    frames, t_fps = 0, time.time()
    turn = 0.0
    t_cam = t_vis = t_mot = 0.0    # acumuladores pra achar o gargalo real
    fps_medido = 30.0              # otimista ate a 1a medicao real
    frame_anterior_confiavel = True

    try:
        while True:
            t0 = time.time()
            ok, frame = cap.read()
            t1 = time.time()
            if not ok:
                motor.stop()
                print("Frame perdido (checa a alimentacao do Pi).")
                continue

            frame = cv2.resize(frame, config.CAMERA_RES)

            # cones: le a ultima deteccao da 2a camera (instantaneo) e deixa
            # a maquina de estados decidir. `desvio.desvio` (0..1) diz o
            # quanto o alvo ja foi deslocado pra ESQUERDA.
            cone = cones.latest() if cones is not None else None
            cone_prev = desvio.estado
            desvio.update(cone)
            if desvio.estado != cone_prev:
                print(f">> CONE: {cone_prev} -> {desvio.estado}")

            res = vision.process(frame, debug=DEBUG, desvio=desvio.desvio)
            t2 = time.time()

            # ---------- maquina de estados ----------
            # IMPORTANTE: checa res.motivo=="ok", nao so res.valid.
            # res.valid fica True durante o "periodo de graca" mesmo em
            # frames de baixa confianca (ex: poucos_pontos), onde o erro
            # fica CONGELADO no ultimo valor bom. Se o PID rodar em cima
            # desse erro congelado e depois um frame fresco chegar com erro
            # bem diferente, o termo D ve isso como um salto violento e
            # dispara um esterco que nao tem nada a ver com a pista real.
            # Por isso, so roda o PID com leitura fresca de verdade.
            if res.valid and res.motivo == "ok" and (res.found_left or res.found_right):
                if not frame_anterior_confiavel:
                    pid.marcar_retomada()   # evita o chute do D nesta transicao
                frame_anterior_confiavel = True

                turn = pid.update(res.error, res.heading)
                # desviando de cone: esterco mais agressivo pra sair rapido
                turn = max(-1.0, min(1.0, turn * desvio.ganho))
                speed = speed_for(turn, res.curvature)

                # TRAVA DE SEGURANCA: se o FPS medido estiver abaixo do minimo
                # seguro pra velocidade configurada, o codigo reduz sozinho.
                # E o que teria evitado o "saiu da pista" com camera a 6 FPS
                # e VELOCIDADE_BASE=0.80 - 0.80 exige FPS alto, ponto fixo.
                if fps_medido < config.FPS_MINIMO_SEGURO:
                    fator_freio = max(0.35, fps_medido / config.FPS_MINIMO_SEGURO)
                    speed *= fator_freio
            elif vision.lost_frames <= config.MAX_FRAMES_PERDIDO:
                # perdeu agora (ou leitura degradada): NAO congela o esterco
                # velho (isso trava o carro numa curva errada). Decai em
                # direcao ao reto, bem devagar.
                frame_anterior_confiavel = False
                turn *= 0.85
                speed = config.VELOCIDADE_PERDIDO
            else:
                turn, speed = 0.0, 0.0
                pid.reset()

            # CONE: ao ver/desviar/voltar, no maximo 20% da velocidade. Vale em
            # qualquer ramo acima (pista ok, perdida...). min() nunca ACELERA.
            if desvio.freando:
                speed = min(speed, config.CONE_VELOCIDADE)

            motor.move(speed, turn)
            t3 = time.time()

            t_cam += (t1 - t0); t_vis += (t2 - t1); t_mot += (t3 - t2)

            # ---------- telemetria ----------
            frames += 1
            if time.time() - t_fps >= 2.0:
                dt = time.time() - t_fps
                fps_medido = frames / dt
                # status honesto: "OK" so quando a leitura E fresca de verdade.
                # Antes isso usava so res.valid, que fica True durante o
                # periodo de graca mesmo em frame degradado -- escondia que
                # o carro ja estava em modo de seguranca (decaindo esterco)
                # atras de um rotulo "OK" enganoso.
                if res.motivo == "ok":
                    status = "OK"
                elif res.valid:
                    status = f"DEGRADADO({res.motivo})"
                else:
                    status = f"PERDIDO({res.motivo})"
                freio = " [FREANDO por FPS baixo]" if fps_medido < config.FPS_MINIMO_SEGURO else ""
                lado = res.lado_continuo or "?"
                print(f"FPS {fps_medido:.1f} | erro {res.error:+.2f} | turn {turn:+.2f} | "
                      f"pts {res.n_pontos} | continua={lado} | {status}{freio}")
                print(f"  termos -> P {pid.last_p:+.2f}  I {pid.last_i:+.2f}  "
                      f"D {pid.last_d:+.2f}  FF {pid.last_ff:+.2f}")
                if cone is not None and cone.found:
                    cone_txt = f"visto (base {cone.y_base_pct*100:.0f}%, x {cone.x_norm:+.2f})"
                else:
                    cone_txt = "nenhum"
                print(f"  cone -> {cone_txt} | estado {desvio.estado} | "
                      f"desvio {desvio.desvio:.2f} | vel max {'20%' if desvio.freando else '-'}")
                print(f"  gargalo -> camera {1000*t_cam/frames:.0f}ms  "
                      f"visao {1000*t_vis/frames:.0f}ms  motor {1000*t_mot/frames:.0f}ms  "
                      f"(por frame)")
                frames, t_fps = 0, time.time()
                t_cam = t_vis = t_mot = 0.0

            if DEBUG and res.debug_view is not None:
                cv2.imshow("Visao", res.debug_view)
                cv2.imshow("Mascara", res.debug_mask)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        print("\nParada de emergencia.")
    finally:
        motor.cleanup()
        cap.release()
        if cones is not None:
            cones.stop()
        cv2.destroyAllWindows()
        print("Desligado com seguranca.")


if __name__ == '__main__':
    main()

