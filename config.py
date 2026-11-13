"""
config.py - todos os parametros do robo num lugar so.
Nenhum outro arquivo tem numero magico dentro.
"""

import numpy as np

# =====================================================================
# 1. HARDWARE (pinos BCM)
# =====================================================================
ENA_A = 5;  IN1_A = 6;  IN2_A = 13     # motor esquerdo
ENA_B = 17; IN3_B = 22; IN4_B = 27     # motor direito
SERVO_PIN = 18

# =====================================================================
# 2. SERVO (graus)
# SERVO_CENTRO nao e o meio geometrico: e o angulo em que a roda fica
# REALMENTE reta. Descubra com: python3 test_servo.py
# =====================================================================
SERVO_CENTRO   = 40
SERVO_MAX_ESQ  = 0
SERVO_MAX_DIR  = 90
SERVO_DEADBAND_DEG = 1.0   # so manda pulso se mudou mais que isso (mata o jitter)

STEER_INVERT = False

# =====================================================================
# 3. VELOCIDADE (0.0 a 1.0)
# =====================================================================
VELOCIDADE_BASE    = 0.55   # baixou de 1.00 -- a 100% a camera/controle nao davam
                            # conta e o carro balancava. Suba de 0.05 em 0.05
                            # so quando estiver andando RETO e estavel.
VELOCIDADE_MINIMA  = 0.35   # baixou de 0.45 -- piso normal de curva
VELOCIDADE_PERDIDO = 0.22   # perdeu a pista, andando devagar procurando

FPS_MINIMO_SEGURO = 15.0

# =====================================================================
# 4. CAMERA
# =====================================================================
CAMERA_RES = (480, 240)

# =====================================================================
# 5. SEGMENTACAO DA FAIXA BRANCA (top-hat, invariante a iluminacao)
# =====================================================================
LINE_MAX_WIDTH_PX = 18
TOPHAT_PERCENTIL  = 98
TOPHAT_FATOR      = 0.45
TOPHAT_MIN        = 18
SAT_MAX           = 90
V_MIN_ABS         = 70
MAX_WHITE_FRAC    = 0.22

# =====================================================================
# 6. VARREDURA (scanline)
# =====================================================================
SCAN_TOP_PCT    = 0.35
SCAN_ROWS       = 14
SCAN_MIN_RUN_PX = 4
SCAN_MIN_ROWS   = 6
SCAN_HW_MIN     = 25
SCAN_HW_MAX     = 160
SCAN_PESO_LONGE = 2.0
SCAN_TRACK_WINDOW = 95

HEADING_MAX          = 1.2
HEADING_SUAVIZACAO   = 0.55

FIT_MIN_PTS_GRAU2 = 6
FIT_MIN_SPAN_PCT  = 0.40
FIT_MARGEM        = 60

LOOKAHEAD_PCT = 0.55
CAR_CENTER_PCT = 0.50

# =====================================================================
# 6b. REACAO EM CURVA
# =====================================================================
FEEDFORWARD_HEADING   = 0.0
SPEED_TURN_PESO       = 1.2    # baixou um pouco de 1.3 -- menos freio pelo
                                # esterco atual, junto com o piso mais alto
SPEED_CURVATURA_PESO  = 75.0   # baixou de 90.0 -- mesma logica

CURVA_FECHADA_LIMIAR     = 0.004
CURVA_FECHADA_RANGE      = 0.014
VELOCIDADE_MINIMA_FECHADA = 0.28   # baixou de 0.38 (tem que ser MENOR que a
                                    # VELOCIDADE_MINIMA) -- piso so pra curva
                                    # bem fechada

# =====================================================================
# 7. CONTROLE (PID)
# Ainda no valor conservador validado (KP=0.50). O procedimento de
# calibracao completo (secao 10) pode liberar um KP mais alto -- isso
# permite corrigir mais forte e rapido, o que deixa CURVAS mais rapidas
# sem precisar abrir mao de margem de seguranca. Vale fazer.
# =====================================================================
PID_KP = 0.62               # baixou de 1.25 -- o teste ESTATICO (carro na
                            # mao) nao revelou instabilidade, mas rodando de
                            # verdade na pista ele oscilou (erro -0.99 seguido
                            # de +0.50 no proximo instante) e saiu da faixa.
                            # 1.25 dinamico = Ku de verdade. Este valor e
                            # Ku*0.5, a regra classica de sempre. So volte a
                            # subir depois de confirmar ESTAVEL rodando na
                            # pista (nao so no teste parado).
PID_KI = 0.0
PID_KD = 0.12                # baixou de 0.15 -- estava dominando o comando
                            # em cima de erro pequeno, com KP=1.25
PID_D_SUAVIZACAO = 0.55      # subiu de 0.3 -- mais filtro na derivada, pra
                            # segurar o balanco sem voltar ao problema antigo
                            # de atraso empilhado (ERRO_SUAVIZACAO continua em
                            # 0.3, entao nao esta dobrando filtro pesado)
PID_I_LIMIT = 0.4
ERRO_SUAVIZACAO = 0.3
DEAD_ZONE = 0.04

# =====================================================================
# 8. SEGURANCA
# =====================================================================
MAX_FRAMES_PERDIDO = 12

# =====================================================================
# 9. VIES DE FAIXA - em que LADO da pista o carro anda
# =====================================================================
# 'direita'  -> o carro anda SEMPRE do lado direito da pista (padrao agora,
#               os cones ficam todos desse lado).
# 'esquerda' -> sempre do lado esquerdo.
# 'auto'     -> comportamento antigo: aprende sozinho qual faixa e a
#               pontilhada e anda colado nela.
LADO_PISTA = 'direita'

# A imagem da camera da PISTA e espelhada em relacao ao mundo real?
# No seu carro SIM: o test_control.py mostra "erro NEGATIVO (alvo a esquerda
# NA IMAGEM) -> servo vai pra DIREITA". Ou seja: esquerda da imagem = DIREITA
# de verdade. Com isso True, 'direita' e o desvio pela 'esquerda' valem no
# MUNDO REAL, nao na imagem.
# COMO CONFERIR (rodas levantadas, python3 Main.py): ponha um cone na frente
# da camera dos cones -> as rodas TEM que virar pra ESQUERDA. Se virarem pra
# direita, troque pra False.
PISTA_IMAGEM_ESPELHADA = True

LANE_BIAS_FRAC   = 0.60     # MAGNITUDE do deslocamento (fracao da meia-largura
                            # da pista). Baixou de 0.85: colado demais na faixa
                            # o carro cruzava a linha ao balancar e perdia o
                            # rastreio -- virava oscilacao. Ainda e DIREITA.
                            # (antes: subiu de 0.70 -- bem mais perto do pontilhado)
LANE_BIAS_LIMITE = 0.90     # subiu de 0.80 -- abriu mais espaco pro vies.
                            # ATENCAO: isso ja come bastante da margem de
                            # seguranca. Perto do limite, qualquer falha
                            # momentanea de deteccao do pontilhado vira erro
                            # grande rapido, porque o alvo ja esta quase
                            # colado nele.

LADO_CONTINUO_SUAVIZACAO = 0.93
LADO_CONTINUO_MARGEM     = 0.15

# TRAVA da decisao de qual lado e continuo. Sem isso, um trecho ruim no meio
# do percurso (esterco violento perdendo o rastreio de um lado, camera
# engasgando) podia derrubar a taxa de deteccao daquele lado por um motivo
# que nao tem nada a ver com o padrao real da faixa, e o codigo TROCAVA de
# decisao no meio do percurso -- o alvo pulava pro lado oposto da pista.
# Agora, uma vez confiante (folga maior que a margem normal, sustentada por
# varios frames seguidos), a decisao trava de vez e para de reagir a
# chacoalhao no resto da execucao.
LADO_CONTINUO_TRAVA_MARGEM = 0.25   # folga maior que LADO_CONTINUO_MARGEM
                                     # pra comecar a contar pra travar
LADO_CONTINUO_TRAVA_FRAMES = 40     # frames CONSISTENTES seguidos pra travar

SAT_LIMITE = 0.95
MAX_FRAMES_SATURADO = 5


# =====================================================================
# 11. CONES (2a camera) + DESVIO
# Os cones ficam sempre do lado DIREITO. Ao ver um, o carro cai pra 20%
# da velocidade, desvia pela ESQUERDA, espera passar e volta pra direita.
# Calibre a cor com: python3 test_cones.py
# =====================================================================
CONE_ATIVO = True           # False = ignora a 2a camera (so segue a pista)

# ---- camera dos cones ----
# Com 2 webcams USB o Linux cria varios /dev/videoN (2 por camera: video0 e
# video1 sao da 1a, video2 e video3 da 2a). Confira com:
#   v4l2-ctl --list-devices
CONE_CAMERA_INDEX = 2
CONE_CAMERA_RES   = (320, 240)   # menor que a da pista: 2 cameras USB dividem
                                 # a banda do barramento do Pi

# ---- cor do cone (HSV do OpenCV: H 0-179) -- aceita LARANJA e VERMELHO ----
# O vermelho "dobra" o H: fica em 0..10 E em 170..179. O laranja fica em ~10..20.
#   faixa 1: CONE_H_MIN..CONE_H_MAX      (0..20)    -> laranja + vermelho-alaranjado
#   faixa 2: CONE_H_VERM_MIN..179        (170..179) -> vermelho puro (o cone da foto: H~174)
CONE_H_MIN     = 0
CONE_H_MAX     = 20
CONE_H_VERM_MIN = 170       # 180 desliga a faixa 2 (so laranja)
CONE_S_MIN     = 110        # saturacao minima (descarta o branco/cinza da pista)
CONE_V_MIN     = 90

# ---- forma / filtro ----
CONE_ROI_TOP_PCT = 0.20     # ignora o topo da imagem (fundo/ceu)
CONE_AREA_MIN    = 150      # px^2 minimo pra contar como cone (anti-ruido)
CONE_ASPECT_MIN  = 0.6      # altura/largura minima do blob (cone e mais alto que largo)

# ---- quando reagir ----
CONE_CONFIRMA_FRAMES = 2    # frames SEGUIDOS vendo o cone pra confirmar
CONE_DESVIO_Y_PCT    = 0.35 # comeca a desviar (antes 0.40: mais cedo, pra dar
                            # distancia pro desvio lento) -- comeca a desviar quando a BASE do cone passa dessa
                            # altura da imagem (0=topo, 1=base). Maior = desvia
                            # mais perto do cone. Ajuste olhando o test_cones.py
CONE_RESULTADO_VALIDADE = 0.5   # s. Leitura da camera mais velha que isso e ignorada

# ---- como desviar ----
CONE_VELOCIDADE   = 0.20    # 20% da velocidade enquanto ve/desvia/volta
CONE_POS_DESVIO   = -0.30   # onde ficar durante o desvio, em fracao da meia-largura
                            # da pista (-1 = colado na faixa esquerda, 0 = centro,
                            # +1 = colado na direita). Negativo = ESQUERDA.
                            # (antes -0.50: movia a pista quase inteira e o carro
                            # passava do ponto e cruzava a linha)
# ATENCAO: a rampa e em TEMPO, mas a 20% de velocidade o carro anda pouco por
# segundo. Rampa rapida = o carro vira tudo e NAO tem chao pra deslocar de
# lado -> passa do ponto e sai da pista. Por isso as rampas sao lentas.
CONE_RAMPA_DESVIO = 1.5     # 1/s. ~0.65 s ate desviar por completo (antes 4.0)
CONE_RAMPA_VOLTA  = 1.0     # 1/s. ~1 s pra voltar pra direita, suave (antes 2.0)
CONE_GANHO_ESTERCO = 1.0    # 1.0 = sem reforco no esterco (antes 1.2/1.5: o
                            # reforco fazia o carro passar do ponto)
CONE_PROCESSA_A_CADA = 2    # a 2a camera analisa 1 a cada N frames (2 = ~15/s).
                            # Alivia a CPU do Pi pra pista nao perder FPS
CONE_TEMPO_PASSAR = 1.2     # s. (antes 0.8: a 20% o carro leva mais tempo pra passar) Depois que o cone SAI da imagem, continua pela
                            # esquerda por esse tempo (o corpo do carro ainda
                            # esta ao lado do cone). Aumente se raspar no cone
                            # ao voltar; diminua se demorar a voltar.


# =====================================================================
# 10. COMO CALIBRAR O PID NO HARDWARE DE VERDADE (pra ganhar velocidade
# de verdade em curva, nao so via piso/freio)
#
# PASSO 1 -- so P (KI=0, KD=0)
#   python3 test_control.py (carro na mao, tracao desligada)
#   Suba PID_KP aos poucos ate o servo comecar a balancar sozinho.
#   Anote esse valor -- e o "Ku".
# PASSO 2 -- PID_KP = Ku * 0.5
# PASSO 3 -- sobe PID_KD aos poucos ate corrigir rapido sem passar do ponto
# PASSO 4 -- so se sobrar erro parado numa reta, sobe PID_KI devagar
#
# Um KP maior valido = correcao mais forte = pode manter mais velocidade
# em curva sem sair. E o proximo ganho real de velocidade depois deste.
# =====================================================================
