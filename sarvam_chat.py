import os
from pathlib import Path

from sarvamai import SarvamAI

env_file = Path(__file__).with_name(".env")
for line in env_file.read_text().splitlines():
    name, separator, value = line.partition("=")
    if separator and name.strip() == "SARVAM_API_KEY":
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))

client = SarvamAI(api_subscription_key=os.environ["SARVAM_API_KEY"])
response = client.chat.completions(
    model="sarvam-105b-conversations",
    messages=[{"role": "user", "content": "Say hello in one sentence."}],
)
print(response.choices[0].message.content)
