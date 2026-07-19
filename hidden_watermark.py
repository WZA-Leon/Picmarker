"""
基于 DWT (离散小波变换) 的隐形水印嵌入/提取模块
替代 blind_watermark 库，支持大图，无尺寸限制
"""
import numpy as np
import pywt
from PIL import Image
from pathlib import Path
import piexif


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
              strength: float = 5.0, wavelet: str = 'haar') -> None:
        """
        嵌入水印到图片

        Args:
            img_path: 输入图片路径
            wm_text: 要嵌入的文本
            output_path: 输出图片路径
            strength: 嵌入强度 (1.0~10.0)，越大越明显但抗攻击性越强
            wavelet: 小波类型，默认 'haar'
        """
        img = Image.open(img_path).convert('RGB')
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

        # 文本转比特 + 16个0作为结束标记
        bits = self._text_to_bits(wm_text) + [0] * 16
        self.wm_bit = bits

        rng = self._init_rng(self.password)
        h_cH, w_cH = cH.shape
        total_pixels = h_cH * w_cH

        if len(bits) > total_pixels:
            raise ValueError(f"水印过长 ({len(bits)} bits)，子带尺寸 {h_cH}x{w_cH}={total_pixels}")

        # 随机选择嵌入位置
        indices = rng.choice(total_pixels, len(bits), replace=False)
        rows = indices // w_cH
        cols = indices % w_cH

        # 嵌入水印到 cH (水平细节子带)
        for idx, (r, c) in enumerate(zip(rows, cols)):
            if bits[idx] == 1:
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

        Image.fromarray(result).save(output_path, quality=95)

        # 保存 EXIF
        try:
            exif_dict = piexif.load(img_path)
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, output_path)
        except Exception as e:
            print(f"EXIF保存失败 ({Path(img_path).name}): {e}")

        # 保存水印长度信息到项目根目录的 len 子文件夹
        project_root = Path(__file__).parent
        len_dir = project_root / "len"
        len_dir.mkdir(exist_ok=True)
        len_path = len_dir / f"{Path(output_path).stem}.len"
        with open(len_path, 'w') as f:
            f.write(str(len(bits)))

    def extract(self, img_path: str, wm_shape: int = None,
                wavelet: str = 'haar') -> str:
        """
        从图片中提取水印

        Args:
            img_path: 图片路径
            wm_shape: 水印比特长度 (从 .len 文件读取)
            wavelet: 小波类型
            

        Returns:
            提取的文本
        """
        img = Image.open(img_path).convert('RGB')
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

        if wm_shape is None:
            # 尝试从项目根目录 len 子文件夹读取
            project_root = Path(__file__).parent
            len_path = project_root / "len" / f"{Path(img_path).stem}.len"
            if len_path.exists():
                with open(len_path) as f:
                    wm_shape = int(f.read())
            else:
                raise FileNotFoundError("未指定 wm_shape 且找不到 len 文件夹下的 .len 文件")

        rng = self._init_rng(self.password)
        indices = rng.choice(total_pixels, wm_shape, replace=False)
        rows = indices // w_cH
        cols = indices % w_cH

        bits = [1 if cH[r, c] > 0 else 0 for r, c in zip(rows, cols)]
        self.wm_bit = bits

        # 找到连续16个0作为结束标记
        text_bits = bits[:]
        for i in range(len(text_bits) - 15):
            if all(b == 0 for b in text_bits[i:i + 16]):
                text_bits = text_bits[:i]
                break
        return self._bits_to_text(text_bits)

