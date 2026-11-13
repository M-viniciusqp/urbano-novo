"""
cone_vision.py - 2a camera: so procura CONES. Nao mexe na pista.

- ConeDetector: funcao pura frame -> ConeResult (testavel sem camera).
- ConeCamera:   abre a 2a camera e roda o detector numa THREAD propria, pra
                a leitura dessa camera nao comer FPS do loop principal (que
                cuida da pista). O main so chama .latest() (instantaneo).
"""

import sys
import threading
import time

import cv2
import numpy as np

import config


class ConeResult:
    __slots__ = ("found", "x_norm", "y_base_pct", "area", "bbox", "t")

    def __init__(self):
        self.found = False
        self.x_norm = 0.0        # -1 (esquerda da imagem) .. +1 (direita)
        self.y_base_pct = 0.0    # 0 = topo .. 1 = base. Quanto maior, mais PERTO
        self.area = 0
        self.bbox = None         # (x, y, w, h) na imagem inteira
        self.t = time.time()     # quando essa leitura foi feita


class ConeDetector:
    def __init__(self):
        self._k_open = np.ones((3, 3), np.uint8)
        # fechamento mais ALTO que largo: junta a parte de cima e a de baixo
        # do cone, que as listras brancas separam em dois blobs laranja
        self._k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 15))
        self.last_mask = None

    def _mask(self, roi):
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lo = np.array([config.CONE_H_MIN, config.CONE_S_MIN, config.CONE_V_MIN], np.uint8)
        hi = np.array([config.CONE_H_MAX, 255, 255], np.uint8)
        mask = cv2.inRange(hsv, lo, hi)
        if config.CONE_H_VERM_MIN < 180:
            lo2 = np.array([config.CONE_H_VERM_MIN, config.CONE_S_MIN, config.CONE_V_MIN], np.uint8)
            hi2 = np.array([179, 255, 255], np.uint8)
            mask |= cv2.inRange(hsv, lo2, hi2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._k_open)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._k_close)
        return mask

    def process(self, frame):
        res = ConeResult()
        H, W = frame.shape[:2]
        y0 = int(H * config.CONE_ROI_TOP_PCT)
        mask = self._mask(frame[y0:, :])
        self.last_mask = mask

        contornos, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        melhor = None            # fica com o cone mais PERTO (base mais baixa)
        for c in contornos:
            area = cv2.contourArea(c)
            if area < config.CONE_AREA_MIN:
                continue
            x, y, w, h = cv2.boundingRect(c)
            if h / float(max(w, 1)) < config.CONE_ASPECT_MIN:
                continue
            base = y0 + y + h
            if melhor is None or base > melhor[0]:
                melhor = (base, x, y0 + y, w, h, area)

        if melhor is not None:
            base, x, y, w, h, area = melhor
            res.found = True
            res.x_norm = ((x + w / 2.0) - W / 2.0) / (W / 2.0)
            res.y_base_pct = base / float(H)
            res.area = int(area)
            res.bbox = (x, y, w, h)
        return res


def abrir_camera_cones():
    # V4L2 so existe no Linux (Raspberry Pi). No Windows/Mac usa o padrao.
    if sys.platform.startswith("linux"):
        cap = cv2.VideoCapture(config.CONE_CAMERA_INDEX, cv2.CAP_V4L2)
    else:
        cap = cv2.VideoCapture(config.CONE_CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CONE_CAMERA_RES[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CONE_CAMERA_RES[1])
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


class ConeCamera:
    """Camera dos cones numa thread. Uso: start() -> latest() -> stop()."""

    def __init__(self):
        self.detector = ConeDetector()
        self.cap = None
        self._lock = threading.Lock()
        self._res = ConeResult()
        self._rodando = False
        self._thread = None

    def start(self):
        self.cap = abrir_camera_cones()
        if not self.cap.isOpened():
            return False
        self._rodando = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def _loop(self):
        while self._rodando:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            frame = cv2.resize(frame, config.CONE_CAMERA_RES)
            res = self.detector.process(frame)
            with self._lock:
                self._res = res

    def latest(self):
        """Ultima leitura. Se a camera travou (leitura velha), devolve 'sem cone'."""
        with self._lock:
            res = self._res
        if time.time() - res.t > config.CONE_RESULTADO_VALIDADE:
            return ConeResult()
        return res

    def stop(self):
        self._rodando = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self.cap is not None:
            self.cap.release()
