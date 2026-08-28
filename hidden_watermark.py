"""
基于 DWT (离散小波变换) 的隐形水印嵌入/提取模块
替代 blind_watermark 库，支持大图，无尺寸限制
"""
import numpy as np
import pywt
from PIL import Image
from pathlib import Path
import piexif
from utils import apply_exif_orientation


class DWTWatermark:
    """基于 DWT 的隐形水印"""

    def __init__(self, password: int = 123456):
        self.password = password
        self.wm_bit = None
        self._rng = None

    def _init_rng(self, seed: int):
        """用密码初始化确定性随机数生成器"""
        return np.random.RandomState(seed)

    def _text_to_bits(self, text: str) -> list:
        """文本 → 比特列表 (每个字符8bit)"""
        bits = []
        for ch in text.encode('utf-8'):
            for i in range(7, -1, -1):
                bits.append((ch >> i) & 1)
        return bits

    def _bits_to_text(self, bits) -> str:
        """比特列表 → 文本"""
        bytes_list = []
        for i in range(0, len(bits) - 7, 8):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | bits[i + j]
            bytes_list.append(byte)
        try:
            return bytes(bytes_list).decode('utf-8', errors='replace')
        except Exception:
            return ""

    def embed(self, img_path: str, wm_text: str, output_path: str,
              strength: float = 5.0, wavelet: str = 'haar', redundancy: int = 5) -> None:
        """
        嵌入水印到图片

        Args:
            img_path: 输入图片路径
            wm_text: 要嵌入的文本
            output_path: 输出图片路径
            strength: 嵌入强度 (1.0~10.0)，越大越明显但抗攻击性越强
            wavelet: 小波类型，默认 'haar'
            redundancy: 每个比特重复嵌入次数，越大越抗压缩但容量越小
        """
        img = apply_exif_orientation(Image.open(img_path)).convert('RGB')
        img_array = np.array(img, dtype=np.float64)

        # RGB → Y (亮度通道)
        y = 0.299 * img_array[:, :, 0] + 0.587 * img_array[:, :, 1] + 0.114 * img_array[:, :, 2]

        h, w = y.shape
        if h % 2 != 0:
            y = np.pad(y, ((0, 1), (0, 0)), mode='reflect')
        if w % 2 != 0:
            y = np.pad(y, ((0, 0), (0, 1)), mode='reflect')

        # DWT
        coeffs = pywt.dwt2(y, wavelet)
        cA, (cH, cV, cD) = coeffs

        # 文本转比特
        text_bits = self._text_to_bits(wm_text)
        # 魔数标记 (16bit)，用于识别是否含水印
        magic = [0x5A5A >> i & 1 for i in range(15, -1, -1)]
        # 长度头 (16bit) + 魔数 + 文本比特
        payload = magic + text_bits
        length_header = [(len(payload) >> i) & 1 for i in range(15, -1, -1)]
        bits = length_header + payload
        self.wm_bit = bits

        rng = self._init_rng(self.password)
        h_cH, w_cH = cH.shape
        total_pixels = h_cH * w_cH

        # 长度头嵌入到固定位置 (前16个像素)，每个比特重复 redundancy 次
        header_positions = []
        for idx in range(16):
            for rep in range(redundancy):
                header_positions.append(idx)
        # 用 rng 为长度头的每个重复生成不同位置（避开文本区）
        header_indices = rng.choice(total_pixels - 16, len(header_positions), replace=False) + 16
        for pos, bit in zip(header_indices, [b for b in length_header for _ in range(redundancy)]):
            r, c = pos // w_cH, pos % w_cH
            if bit == 1:
                cH[r, c] = abs(cH[r, c]) + strength
            else:
                cH[r, c] = -abs(cH[r, c]) - strength

        # 文本比特嵌入到随机位置（避开长度头区域），每个比特重复 redundancy 次
        text_with_end = payload
        total_bits = len(text_with_end) * redundancy
        text_indices = rng.choice(total_pixels - 16, total_bits, replace=False) + 16
        for pos, bit in zip(text_indices, [b for b in text_with_end for _ in range(redundancy)]):
            r, c = pos // w_cH, pos % w_cH
            if bit == 1:
                cH[r, c] = abs(cH[r, c]) + strength
            else:
                cH[r, c] = -abs(cH[r, c]) - strength
        # IDWT
        y_watermarked = pywt.idwt2((cA, (cH, cV, cD)), wavelet)[:h, :w]

        # Y → RGB (保持色度不变)
        result = img_array.copy()
        y_orig = 0.299 * img_array[:, :, 0] + 0.587 * img_array[:, :, 1] + 0.114 * img_array[:, :, 2]
        # 计算 Y 通道的变化量，应用到 RGB 各通道
        diff = y_watermarked - y_orig
        for c in range(3):
            result[:, :, c] = np.clip(img_array[:, :, c] + diff, 0, 255)
        result = result.astype(np.uint8)

        # 先读取原始 EXIF（必须在覆盖 output_path 之前，因为 img_path 可能等于 output_path）
        exif_bytes = None
        try:
            exif_dict = piexif.load(img_path)
            # 已有的EXIF项强制原样保留，不做任何修改
            if exif_dict:
                exif_bytes = piexif.dump(exif_dict)
        except Exception as e:
            print(f"EXIF读取失败 ({Path(img_path).name}): {e}")

        # 保存图片（有EXIF时直接携带原EXIF，避免二次插入冲突）
        if exif_bytes:
            Image.fromarray(result).save(output_path, quality=95, exif=exif_bytes)
        else:
            Image.fromarray(result).save(output_path, quality=95)

    def extract(self, img_path: str, wm_shape: int = None,
                wavelet: str = 'haar', redundancy: int = 5) -> str:
        """
        从图片中提取水印

        Args:
            img_path: 图片路径
            wm_shape: 水印比特长度 (从长度头自动读取)
            wavelet: 小波类型
            redundancy: 冗余次数，需与嵌入一致

        Returns:
            提取的文本
        """
        img = apply_exif_orientation(Image.open(img_path)).convert('RGB')
        img_array = np.array(img, dtype=np.float64)

        y = 0.299 * img_array[:, :, 0] + 0.587 * img_array[:, :, 1] + 0.114 * img_array[:, :, 2]

        h, w = y.shape
        if h % 2 != 0:
            y = np.pad(y, ((0, 1), (0, 0)), mode='reflect')
        if w % 2 != 0:
            y = np.pad(y, ((0, 0), (0, 1)), mode='reflect')

        coeffs = pywt.dwt2(y, wavelet)
        cA, (cH, cV, cD) = coeffs

        h_cH, w_cH = cH.shape
        total_pixels = h_cH * w_cH

        # 从固定位置读取长度头（前16个像素，每个重复 redundancy 次，多数投票）
        rng = self._init_rng(self.password)
        header_indices = rng.choice(total_pixels - 16, 16 * redundancy, replace=False) + 16
        header_votes = [[] for _ in range(16)]
        for i, pos in enumerate(header_indices):
            r, c = pos // w_cH, pos % w_cH
            header_votes[i // redundancy].append(1 if cH[r, c] > 0 else 0)
        header_bits = [1 if sum(v) > redundancy // 2 else 0 for v in header_votes]
        text_len = 0
        for b in header_bits:
            text_len = (text_len << 1) | b

        # 文本比特
        wm_shape = text_len

        # 文本比特（多数投票）
        total_bits = wm_shape * redundancy
        indices = rng.choice(total_pixels - 16, total_bits, replace=False) + 16
        votes = [[] for _ in range(wm_shape)]
        for i, pos in enumerate(indices):
            r, c = pos // w_cH, pos % w_cH
            votes[i // redundancy].append(1 if cH[r, c] > 0 else 0)
        bits = [1 if sum(v) > redundancy // 2 else 0 for v in votes]
        self.wm_bit = bits

        # 校验魔数标记，判断是否含水印
        if wm_shape >= 16:
            magic_bits = bits[:16]
            magic = 0
            for b in magic_bits:
                magic = (magic << 1) | b
            if magic != 0x5A5A:
                return "没有水印"
            text_bits = bits[16:wm_shape]
        else:
            return "没有水印"
        return self._bits_to_text(text_bits)

