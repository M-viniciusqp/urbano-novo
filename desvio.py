"""
desvio.py - maquina de estados do desvio de cone.

Os cones ficam sempre do lado DIREITO e o carro anda sempre do lado direito.
Entao a manobra e sempre a mesma:

    SEGUE  --(cone confirmado e perto)-->  DESVIA  (vai pra ESQUERDA, rapido)
    DESVIA --(cone sumiu + tempo de passar)--> VOLTA (volta pra DIREITA)
    VOLTA  --(chegou na direita)-->        SEGUE
    VOLTA  --(outro cone)-->               DESVIA

Este modulo nao sabe nada de pixel nem de motor. Ele so produz:
  - desvio  : 0.0 (posicao normal, direita) .. 1.0 (desviado, esquerda).
              O vision.py transforma isso na posicao lateral do alvo.
  - freando : True enquanto a velocidade deve ficar limitada a 20%.
  - ganho   : multiplicador do esterco (desvio mais agressivo).
"""

import time
import config

SEGUE = "SEGUE"
DESVIA = "DESVIA"
VOLTA = "VOLTA"


class DesvioCone:
    def __init__(self):
        self.estado = SEGUE
        self.desvio = 0.0
        self._frames_cone = 0
        self._t_ultimo_cone = 0.0
        self._t_prev = None

    @property
    def freando(self):
        """Limita a velocidade assim que um cone e CONFIRMADO (mesmo longe) e
        ate terminar de voltar pra direita."""
        return self.estado != SEGUE or self._frames_cone >= config.CONE_CONFIRMA_FRAMES

    @property
    def ganho(self):
        return config.CONE_GANHO_ESTERCO if self.estado != SEGUE else 1.0

    def update(self, cone, now=None):
        """cone: ConeResult (ou None se a 2a camera esta desligada)."""
        now = time.time() if now is None else now
        dt = 0.0 if self._t_prev is None else max(0.0, min(0.2, now - self._t_prev))
        self._t_prev = now

        visto = cone is not None and cone.found
        self._frames_cone = self._frames_cone + 1 if visto else 0
        confirmado = self._frames_cone >= config.CONE_CONFIRMA_FRAMES
        perto = confirmado and cone.y_base_pct >= config.CONE_DESVIO_Y_PCT
        if confirmado:
            self._t_ultimo_cone = now

        if self.estado == SEGUE:
            if perto:
                self.estado = DESVIA
        elif self.estado == DESVIA:
            # cone ainda na imagem refresca _t_ultimo_cone (acima). So volta
            # depois que ele sumiu E o corpo do carro ja passou por ele.
            if not confirmado and now - self._t_ultimo_cone > config.CONE_TEMPO_PASSAR:
                self.estado = VOLTA
        elif self.estado == VOLTA:
            if perto:                       # outro cone no meio da volta
                self.estado = DESVIA
            elif self.desvio <= 0.001:
                self.estado = SEGUE

        alvo = 1.0 if self.estado == DESVIA else 0.0
        rampa = config.CONE_RAMPA_DESVIO if alvo > self.desvio else config.CONE_RAMPA_VOLTA
        passo = rampa * dt
        self.desvio += max(-passo, min(passo, alvo - self.desvio))
        if self.estado == SEGUE:
            self.desvio = 0.0

    def reset(self):
        self.__init__()
