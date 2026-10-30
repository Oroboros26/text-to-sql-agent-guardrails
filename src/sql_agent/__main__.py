import sys

from .agent import run

print(run(" ".join(sys.argv[1:]))["answer"])
