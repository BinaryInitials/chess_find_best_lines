import chess
import chess.engine
import json
import re
import subprocess
import sys

DEFAULT_ENGINE="stockfish"
ONE_SECOND = 1

def initialize_engine(engine_name=DEFAULT_ENGINE, options={}):
	engine = chess.engine.SimpleEngine.popen_uci(f"./{engine_name}")
	for key in options.keys():
		engine.configure({key: options[key]})
	return engine


def close_engine(engine):
	engine.quit()

def analyze_board(engine, board, move_time=0.1):
	info = engine.analyse(board, chess.engine.Limit(depth=100, time=move_time))
	result = {}
	result["san"] = board.san(info["pv"][0])
	score = info["score"]
	result["is_mate"] = score.is_mate()
	if result["is_mate"]:
		result["score"] = f"mate {score.relative.mate()}"
		result["score_int"] = 10000 - abs(score.relative.mate())
	else:
		result["score"] = score.relative.cp
		result["score_int"] = score.relative.cp
	return result

if __name__ == "__main__":
	USAGE = "[fen]"
	if len(sys.argv) < 2:
		print(f"[ERROR] Usage {USAGE}")
		exit()

	fen = sys.argv[1]
	timeout = 1000
	if len(sys.argv) > 2:
		timeout = sys.argv[2]

	board = chess.Board(fen)
	engine = initialize_engine()
	result = analyze_board(engine, board, ONE_SECOND)
	print(json.dumps(result, indent=2))
	close_engine(engine)
