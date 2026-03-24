from config.env import env


AMAN_GATE_API_TOKEN = env.str("AMAN_GATE_API_TOKEN", default="")
AMAN_GATE_TEMPLATE_ID = env.int("AMAN_GATE_TEMPLATE_ID", default=1)
