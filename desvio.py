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
        self._giro_ini = None       # quando comecou o giro no limite (None = sem giro)
        self._giro_viu_esq = False  # o erro ja mostrou o alvo a esquerda neste giro
        self.evento = None          # texto pro log do Main (ele imprime e limpa)

    @staticmethod
    def _esq():
        """Sinal do turn que vira a roda pra ESQUERDA (-1 com STEER_INVERT=False)."""
        return 1.0 if config.STEER_INVERT else -1.0

    def ajustar_turn(self, turn, res, now=None):
        """Chamar DEPOIS do PID, com o turn final. So mexe no estado DESVIA:
        - nunca deixa o servo virar pra DIREITA (pro lado do cone);
        - no comeco do desvio, servo no LIMITE da esquerda ate o carro chegar
          na posicao da esquerda (erro ~0) ou ate CONE_GIRO_MAX_S."""
        if self.estado != DESVIA:
            return turn
        now = time.time() if now is None else now
        esq = self._esq()
        turn = min(turn, 0.0) if esq < 0 else max(turn, 0.0)   # nunca pro cone
        if config.CONE_GIRO_LIMITE and self._giro_ini is not None:
            ok = res is not None and res.valid and res.motivo == "ok"
            # erro (imagem): negativo = alvo ainda a ESQUERDA do carro. So conta
            # "chegou" DEPOIS de ter visto o alvo a esquerda: no 1o quadro do
            # desvio o erro ainda e o de antes (suavizado) e soltaria na hora.
            if ok and res.error < -config.CONE_GIRO_SOLTA_ERRO:
                self._giro_viu_esq = True
            chegou = ok and self._giro_viu_esq and res.error >= -config.CONE_GIRO_SOLTA_ERRO
            if chegou:
                self._giro_ini = None
                self.evento = "giro solto: chegou na esquerda"
            elif now - self._giro_ini > config.CONE_GIRO_MAX_S:
                self._giro_ini = None
                self.evento = "giro solto: tempo maximo"
            else:
                turn = esq * 1.0                    # servo no LIMITE da esquerda
        return turn

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
                self._giro_ini, self._giro_viu_esq = now, False
                self.evento = "servo no LIMITE da esquerda"
        elif self.estado == DESVIA:
            # cone ainda na imagem refresca _t_ultimo_cone (acima). So volta
            # depois que ele sumiu E o corpo do carro ja passou por ele.
            if not confirmado and now - self._t_ultimo_cone > config.CONE_TEMPO_PASSAR:
                self.estado = VOLTA
                self._giro_ini = None
        elif self.estado == VOLTA:
            if perto:                       # outro cone no meio da volta
                self.estado = DESVIA
                self._giro_ini, self._giro_viu_esq = now, False
                self.evento = "servo no LIMITE da esquerda"
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
