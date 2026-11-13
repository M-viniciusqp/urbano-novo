"""
test_cones.py - testa SO a 2a camera (cones). Nao toca em GPIO, nao liga motor.
Use pra calibrar a COR do cone e o ponto onde o desvio comeca.

    python3 test_cones.py              # camera ao vivo (CONE_CAMERA_INDEX)
    python3 test_cones.py 0            # outra camera
    python3 test_cones.py foto.jpg     # imagem parada

O que olhar:
  - Janela "Cones": retangulo VERDE = cone detectado. A linha AMARELA e o
    ponto onde o desvio comeca (CONE_DESVIO_Y_PCT): quando a BASE do cone
    cruza a linha, o carro comeca a desviar.
  - Janela "Mascara": so o cone deve ficar branco. Se pegar chao/parede,
    suba a saturacao ('d'). Se nao pegar o cone, desca ('a').

Teclas:
  a / d  -> CONE_S_MIN  -/+     (saturacao minima)
  z / x  -> CONE_V_MIN  -/+     (brilho minimo)
  g / h  -> CONE_H_MAX  -/+     (faixa de cor, 20 = laranja)
  w / s  -> CONE_DESVIO_Y_PCT -/+  (onde comeca o desvio)
  q      -> sai e imprime os valores pra colar no config.py
"""

import sys
import cv2

import config
from cone_vision import ConeDetector, abrir_camera_cones


def desenhar(frame, res):
    vis = frame.copy()
    H, W = vis.shape[:2]
    y_lim = int(H * config.CONE_DESVIO_Y_PCT)
    cv2.line(vis, (0, y_lim), (W, y_lim), (0, 255, 255), 1)
    if res.found:
        x, y, w, h = res.bbox
        desvia = res.y_base_pct >= config.CONE_DESVIO_Y_PCT
        cor = (0, 0, 255) if desvia else (0, 255, 0)     # vermelho = ja desviaria
        cv2.rectangle(vis, (x, y), (x + w, y + h), cor, 2)
        txt = (f"CONE base {res.y_base_pct*100:.0f}% x {res.x_norm:+.2f} "
               f"area {res.area}" + ("  -> DESVIA" if desvia else ""))
    else:
        txt = "sem cone"
    cv2.putText(vis, txt, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    cv2.putText(vis, f"S>={config.CONE_S_MIN} V>={config.CONE_V_MIN} "
                     f"H<={config.CONE_H_MAX} desvio_y={config.CONE_DESVIO_Y_PCT:.2f}",
                (6, H - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    return vis


def tratar_tecla(k):
    if k == ord('d'):
        config.CONE_S_MIN = min(255, config.CONE_S_MIN + 10)
    elif k == ord('a'):
        config.CONE_S_MIN = max(0, config.CONE_S_MIN - 10)
    elif k == ord('x'):
        config.CONE_V_MIN = min(255, config.CONE_V_MIN + 10)
    elif k == ord('z'):
        config.CONE_V_MIN = max(0, config.CONE_V_MIN - 10)
    elif k == ord('h'):
        config.CONE_H_MAX = min(35, config.CONE_H_MAX + 1)
    elif k == ord('g'):
        config.CONE_H_MAX = max(0, config.CONE_H_MAX - 1)
    elif k == ord('s'):
        config.CONE_DESVIO_Y_PCT = round(min(0.95, config.CONE_DESVIO_Y_PCT + 0.02), 2)
    elif k == ord('w'):
        config.CONE_DESVIO_Y_PCT = round(max(0.05, config.CONE_DESVIO_Y_PCT - 0.02), 2)
    elif k == ord('q'):
        return False
    return True


def main():
    det = ConeDetector()
    arg = sys.argv[1] if len(sys.argv) > 1 else None

    # ---- imagem parada
    if arg and arg.lower().endswith(('.jpg', '.jpeg', '.png')):
        frame = cv2.resize(cv2.imread(arg), config.CONE_CAMERA_RES)
        while True:
            res = det.process(frame)
            cv2.imshow("Cones", desenhar(frame, res))
            cv2.imshow("Mascara", det.last_mask)
            if not tratar_tecla(cv2.waitKey(0) & 0xFF):
                break
    else:
        if arg is not None and arg.isdigit():
            config.CONE_CAMERA_INDEX = int(arg)
        cap = abrir_camera_cones()
        if not cap.isOpened():
            print(f"Camera {config.CONE_CAMERA_INDEX} nao abriu. "
                  f"Rode 'v4l2-ctl --list-devices'.")
            return
        while True:
            ok, frame = cap.read()
            if not ok:
                continue
            frame = cv2.resize(frame, config.CONE_CAMERA_RES)
            res = det.process(frame)
            cv2.imshow("Cones", desenhar(frame, res))
            cv2.imshow("Mascara", det.last_mask)
            if not tratar_tecla(cv2.waitKey(1) & 0xFF):
                break
        cap.release()

    cv2.destroyAllWindows()
    print(f"\nCole no config.py:"
          f"\n  CONE_S_MIN         = {config.CONE_S_MIN}"
          f"\n  CONE_V_MIN         = {config.CONE_V_MIN}"
          f"\n  CONE_H_MAX         = {config.CONE_H_MAX}"
          f"\n  CONE_DESVIO_Y_PCT  = {config.CONE_DESVIO_Y_PCT:.2f}\n")


if __name__ == '__main__':
    main()
