"""Pure text splitting. Offsets are Unicode codepoints, 0-based [start, end)."""
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Piece:
    text: str
    start: int
    end: int
    coordinate_space: str

def options(raw=None):
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError('切分参数必须为对象')
    strategy = raw.get('strategy', 'auto')
    if strategy not in ('auto', 'custom', 'hierarchy'):
        raise ValueError('未知切分策略')
    if strategy != 'custom':
        return {'strategy': strategy, 'max_length': 800, 'overlap': 0.1}
    length, overlap = raw.get('max_length', 800), raw.get('overlap', 0.1)
    if type(length) is not int or not 100 <= length <= 2000:
        raise ValueError('最大长度必须是100–2000的整数')
    if type(overlap) not in (int, float) or not 0 <= overlap <= 0.5:
        raise ValueError('重叠比例必须在0–0.5之间')
    delimiter = raw.get('delimiter', '\n\n')
    if not isinstance(delimiter, str) or not 1 <= len(delimiter) <= 40:
        raise ValueError('分隔符长度必须为1–40字符')
    for k in ('remove_urls', 'collapse_whitespace'):
        if k in raw and type(raw[k]) is not bool:
            raise ValueError('预处理选项必须为布尔值')
    return {'strategy': strategy, 'max_length': length, 'overlap': overlap,
            'delimiter': delimiter, 'remove_urls': raw.get('remove_urls', False),
            'collapse_whitespace': raw.get('collapse_whitespace', False)}

def split_text(original, raw=None):
    opt = options(raw)
    text = original
    if opt.get('remove_urls'):
        text = re.sub(r'https?://[^\s<>]+|[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', '', text)
    if opt.get('collapse_whitespace'):
        text = re.sub(r'\s+', ' ', text)
    space = 'original' if text == original else 'processed'
    spans = [(0, len(text))]
    if opt['strategy'] == 'hierarchy':
        starts = [m.start() for m in re.finditer(r'^#{1,3}\s+', text, re.M)]
        cuts = sorted(set([0, *starts, len(text)]))
        spans = list(zip(cuts, cuts[1:]))
    pieces = []
    limit, overlap = opt['max_length'], int(opt['max_length'] * opt['overlap'])
    delimiters = [opt['delimiter']] if opt['strategy'] == 'custom' else ['\n\n', '\n', '。', '. ']
    for begin, finish in spans:
        start = begin
        while start < finish:
            end = min(start + limit, finish)
            if end < finish:
                for delimiter in delimiters:
                    at = text.rfind(delimiter, start + max(overlap + 1, limit // 2), end)
                    if at >= 0:
                        end = at + len(delimiter)
                        break
            if text[start:end].strip():
                pieces.append(Piece(text[start:end], start, end, space))
            if end == finish:
                break
            start = max(start + 1, end - overlap)
    return text, pieces, opt
