"""
desvio.py - maquina de estados do desvio de cone.

Os cones ficam sempre do lado DIREITO e o carro anda sempre do lado direito.
Entao a manobra e sempre a mesma:

    SEGUE  --(cone confirmado e perto)-->  DESVIA  (vai pra ESQUERDA, servo no limite)
    DESVIA --(cone sumiu + tempo de passar)--> VOLTA (volta pra DIREITA)
    VOLTA  --(chegou na direita)-->        SEGUE
    VOLTA  --(outro cone)-->               DESVIA

Este modulo nao sabe nada de pixel nem de motor. Ele so produz:
  - desvio  : 0.0 (posicao normal, direita) .. 1.0 (desviado, esquerda).
              O vision.py transforma isso na posicao lateral do alvo.
  - freando : True enquanto a velocidade deve ficar limitada a 20%.
  - ganho   : multiplicador do esterco.
  - ajustar_turn(): no DESVIA, servo no LIMITE da esquerda enquanto o cone
              estiver na frente, e nunca vira pro lado do cone.

SENTIDO (confirmado no corrida-cone2, mesmo MotorModule): turn NEGATIVO =
roda pra ESQUERDA (servo -> SERVO_MAX_ESQ).
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
        self._giro_ini = None       # inicio da fase de giro no limite (None = acabou)
        self._giro_viu_esq = False  # o erro ja mostrou o alvo a esquerda nesta fase
        self.no_limite = False      # servo no limite da esquerda AGORA (pro log)
        self.evento = None          # texto pro log do Main (ele imprime e limpa)

    @staticmethod
    def _esq():
        """Sinal do turn que vira a roda pra ESQUERDA (-1 com STEER_INVERT=False)."""
        return 1.0 if config.STEER_INVERT else -1.0

    def _entra_desvia(self, now):
        self.estado = DESVIA
        self._giro_ini, self._giro_viu_esq = now, False

    def ajustar_turn(self, turn, res, cone=None, now=None):
        """Chamar DEPOIS do PID, com o turn final. So mexe no estado DESVIA.

        Ordem de prioridade (as duas regras do usuario):
          1. NAO SAIR DA PISTA: carro chegou na borda ESQUERDA -> para de virar
             pra esquerda (reto se o cone ainda esta na frente; senao o PID
             traz de volta).
          2. NAO BATER NO CONE: enquanto o cone estiver na frente do carro (ou
             no comeco do desvio), servo no LIMITE da esquerda.
          3. No resto do desvio, o PID segura a posicao, mas nunca vira pra
             DIREITA (pro lado do cone).
        """
        if self.estado != DESVIA:
            self._marca_limite(False)
            return turn
        now = time.time() if now is None else now
        esq = self._esq()

        ok = res is not None and res.valid and res.motivo == "ok"
        pos = res.pos_carro if (ok and getattr(res, "pos_carro", None) is not None) else None
        cone_frente = (cone is not None and cone.found and
                       cone.x_esq < config.CONE_X_LIVRE)

        # 1. borda esquerda da pista: prioridade sobre o giro
        if pos is not None and pos <= -config.CONE_LIMITE_ESQ:
            if self._giro_ini is not None or self.no_limite:
                self.evento = "giro solto: carro na BORDA ESQUERDA da pista"
            self._giro_ini = None
            self._marca_limite(False)
            return 0.0 if cone_frente else turn

        # 2. fase inicial do giro (mesmo antes do cone "entrar na frente")
        if config.CONE_GIRO_LIMITE and self._giro_ini is not None:
            # erro (imagem): negativo = alvo ainda a ESQUERDA do carro. So conta
            # "chegou" DEPOIS de ter visto o alvo a esquerda: no 1o quadro do
            # desvio o erro ainda e o de antes (suavizado) e soltaria na hora.
            if ok and res.error < -config.CONE_GIRO_SOLTA_ERRO:
                self._giro_viu_esq = True
            chegou = ok and self._giro_viu_esq and res.error >= -config.CONE_GIRO_SOLTA_ERRO
            if now - self._giro_ini > config.CONE_GIRO_MAX_S or (chegou and not cone_frente):
                self._giro_ini = None
            else:
                self._marca_limite(True)
                return esq * 1.0

        # 2b. cone ainda NA FRENTE do carro: limite da esquerda, sem tempo maximo
        if config.CONE_GIRO_LIMITE and cone_frente:
            self._marca_limite(True)
            return esq * 1.0

        # 3. segura a posicao com o PID, nunca pro lado do cone
        self._marca_limite(False)
        return min(turn, 0.0) if esq < 0 else max(turn, 0.0)

    def _marca_limite(self, no_limite):
        if no_limite != self.no_limite:
            self.evento = ("servo no LIMITE da esquerda" if no_limite
                           else (self.evento or "servo saiu do limite (cone fora do caminho)"))
        self.no_limite = no_limite

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
                self._entra_desvia(now)
        elif self.estado == DESVIA:
            # cone ainda na imagem refresca _t_ultimo_cone (acima). So volta
            # depois que ele sumiu E o corpo do carro ja passou por ele.
            if not confirmado and now - self._t_ultimo_cone > config.CONE_TEMPO_PASSAR:
                self.estado = VOLTA
                self._giro_ini = None
        elif self.estado == VOLTA:
            if perto:                       # outro cone no meio da volta
                self._entra_desvia(now)
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
