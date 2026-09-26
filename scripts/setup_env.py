"""Create credentials locally; never print API keys and never overwrite an existing .env."""
from pathlib import Path
import secrets
root=Path(__file__).resolve().parents[1]
path=root/'.env'
if path.exists():
    print('.env 已存在，保持不变。')
else:
    data=(root/'.env.example').read_text()
    data=data.replace('replace_with_random_letters_and_digits',secrets.token_hex(20))
    data=data.replace('replace_with_another_random_password',secrets.token_hex(24))
    data=data.replace('replace_with_your_demo_password',secrets.token_urlsafe(12))
    path.touch(mode=0o600)
    path.write_text(data)
    print('已创建 .env。四个演示账号使用其中的 DEMO_PASSWORD。')
