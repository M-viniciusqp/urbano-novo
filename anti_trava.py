"""
anti_trava.py - o motor nao sai do lugar em velocidade baixa.

No corrida-cone2 (teste real) o carro ficou PARADO 6 s mandando 0.20: abaixo
de ~0.22 o motor nao vence o atrito do repouso. Em movimento ele aguenta 0.20.

Solucao (a mesma do corrida-cone2): mede quanto a imagem da camera da PISTA
mudou de um quadro pro outro. Mandando andar e a imagem PARADA por
ANTI_TRAVA_S -> da um pulso curto de ANTI_TRAVA_VEL pra arrancar; depois
volta pra velocidade baixa.
"""

import cv2
import numpy as np
import config


class AntiTrava:
    def __init__(self):
        self._ant = None
        self._t_trava = None
        self._pulso_ate = 0.0
        self.mov = None          # quanto o chao mexeu (0-255). Pro log
        self.evento = None

    def medir(self, frame):
        """Chamar com o frame da camera da PISTA, todo quadro."""
        peq = cv2.cvtColor(cv2.resize(frame, (64, 36), interpolation=cv2.INTER_AREA),
                           cv2.COLOR_BGR2GRAY).astype(np.float32)
        peq -= float(peq.mean())        # luz/auto-exposicao oscilando nao conta como movimento
        self.mov = float(np.abs(peq - self._ant).mean()) if self._ant is not None else None
        self._ant = peq

    def ajustar(self, speed, now):
        """Devolve a velocidade, com o pulso se o carro estiver travado."""
        if not config.ANTI_TRAVA_ATIVO or speed < 0.05 or self.mov is None:
            self._t_trava = None
            return speed
        if self.mov < config.ANTI_TRAVA_DIFF:
            if self._t_trava is None:
                self._t_trava = now
            elif now - self._t_trava >= config.ANTI_TRAVA_S:
                self._pulso_ate = now + config.ANTI_TRAVA_PULSO_S
                self._t_trava = None
                self.evento = "carro nao saiu do lugar -> pulso anti-trava"
        else:
            self._t_trava = None
        if now < self._pulso_ate:
            return max(speed, config.ANTI_TRAVA_VEL)
        return speed
