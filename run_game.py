import argparse
import chess
import datetime
import json
import lichess
import random
import re
import stockfish

WALL = "|"
EMPTY_CELL = "   "
COLOR_NC='\033[0m' # No Color
COLOR_BLACK='\033[30m'
COLOR_GRAY='\033[30m'
COLOR_RED='\033[31m'
COLOR_LIGHT_RED='\033[31m'
COLOR_GREEN='\033[32m'
COLOR_LIGHT_GREEN='\033[32m'
COLOR_BROWN='\033[33m'
COLOR_YELLOW='\033[33m'
COLOR_BLUE='\033[34m'
COLOR_LIGHT_BLUE='\033[34m'
COLOR_PURPLE='\033[35m'
COLOR_LIGHT_PURPLE='\033[35m'
COLOR_CYAN='\033[36m'
COLOR_LIGHT_CYAN='\033[36m'
COLOR_LIGHT_GRAY='\033[37m'
COLOR_WHITE='\033[37m'
BOUNDARY = "   " + "-"*33
LAST_ROW = "  A   B   C   D   E   F   G   H  "

DEFAULT_STOCKFISH_TIMEOUT = stockfish17.ONE_SECOND

def print_board(board):
	print(BOUNDARY)
	for i in range(7,-1,-1):
		row = f" {i+1} |"
		for j in range(0, 8):
			piece_index = i*8+j	
			piece = " "
			color = COLOR_NC
			if board.piece_at(piece_index) != None:
				piece = board.piece_at(piece_index).symbol()
				color = COLOR_GREEN if piece.isupper() else COLOR_RED
				piece = piece.upper()
			row += f"{color} {piece} {COLOR_NC}|"
		print(row)
		print(BOUNDARY)
	print(LAST_ROW)
	
PIECE_MAP = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 200, "p": -1, "n": -3, "b": -3, "r": -5, "q": -9, "k": -200}
LICHESS_TOTAL_COUNT_TRESHOLD = 10
def timestamp(now):
	return "{:04d}{:02d}{:02d}".format(now.year, now.month, now.day)

def timer():
	return datetime.datetime.now()

def dt(time):
	return (timer() - time).total_seconds()

def write_to_file(filename, lines):
	with open(filename, "w") as file_buffer:
		for line in lines:
			file_buffer.writelines(line + "\n")

def get_score(board):
	score = 0
	for piece in board.piece_map().values():
		score += PIECE_MAP[piece.__str__()]
	return score

def get_pgn(move_history):
	pgn = ""
	move_ply = 0
	move_number = 0
	for move in move_history:
		move_ply += 1
		if move_ply % 2 == 1:
			move_number+=1
			pgn += f"{move_number}.{move} "
		else:
			pgn += f"{move} "
	return pgn

def run_game_lines(engine, human_engine, board, move_history, pgns, last_lichess_total, stockfish_turn, threshold=0.25, debug_mode=False, skip_lichess=False, stockfish_timeout=DEFAULT_STOCKFISH_TIMEOUT, fen_cache=[]):
	fen = board.fen()

	if board.turn == (stockfish_turn == "w"):
		pgn = get_pgn(move_history)
		pgn_move_number = int((len(pgn.split(' ')))/2)+1
		dots = "." if board.turn else ".. "
		move = stockfish17.analyze_board(engine, board, stockfish_timeout)
		board.push_san(move['san']);
		fen_cache.append(board.fen().split(' ')[0])

		if move["is_mate"]:
			last_move = move_history.pop();
			move_history.append(last_move + "{" + move["score"] + "}");
			move_history.append(move['san'] + "{" + move['score'] + "}")
		else:
			move_history.append(move['san'])

		if debug_mode:
			print_board(board)
			print(fen)
			print(get_pgn(move_history))
			if move["is_mate"]:
				print(f"[GAME #{len(pgns)+1}][STOCKFISH]{pgn_move_number}{dots}{move['san']} [MATE DETECTION] {move['score']}, fen={board.fen()}")
			else:
				print(f"[GAME #{len(pgns)+1}][STOCKFISH]{pgn_move_number}{dots}{move['san']}, fen={board.fen()}")

		if board.is_game_over():
			pgn = get_pgn(move_history)
			print(f"#{len(pgns)+1}\t{pgn}")
			pgns.append(pgn)
			board.pop()
			move_history.pop()

			if debug_mode:
				print("----------------------------")
				print()
				print(f"[NEW GAME] GAME #{len(pgns)+1} STARTS NOW")

			return

	lichess_moves = []
	if last_lichess_total > LICHESS_TOTAL_COUNT_TRESHOLD:
		lichess_object = lichess.get_lichess_data(move_history)
		lichess_moves = lichess_object["moves"]
		last_lichess_total = lichess_object["total"]
		if len(lichess_moves) == 0:
			last_lichess_total = 0
	
	pgn = get_pgn(move_history)
	pgn_move_number = int((len(pgn.split(' ')))/2)+1
	dots = "." if board.turn else ".. "

	if len(lichess_moves) > 0 and last_lichess_total > LICHESS_TOTAL_COUNT_TRESHOLD and not skip_lichess:
		move_number = 0

		previous_percentage_played = None
		for lichess_move in lichess_moves:

			if lichess_move["percentage_played"] < threshold and previous_percentage_played != None and previous_percentage_played - lichess_move["percentage_played"] > 0.005:
				if debug_mode:
					print(f"[GAME #{len(pgns)+1}][LICHESS {move_number+1}]{pgn_move_number}{dots}{lichess_move['move_san']} skipping because: play%={round(100*lichess_move['percentage_played'],1)}%, previous_play%={round(100*previous_percentage_played,1)}%")
					print(f"[GAME #{len(pgns)+1}][LICHESS {move_number+1}]{pgn_move_number}{dots}{lichess_move['move_san']} pgn: {get_pgn(move_history)}")
				break
			previous_percentage_played_previous = previous_percentage_played
			previous_percentage_played = lichess_move["percentage_played"]

			move_number +=1
			board.push_san(lichess_move['move_san'])

			# Checking to see if this move leads to a transpose of a previously analyzed board
			fen_key = board.fen().split(" ")[0]
			if fen_key in fen_cache:
				if debug_mode:
					print(f"[GAME #{len(pgns)+1}][LICHESS {move_number+1}]{pgn_move_number}{dots}{lichess_move['move_san']} skipping transpose: {fen_key}")
				board.pop()
				continue

			fen_cache.append(board.fen().split(" ")[0])
			move_history.append(lichess_move['move_san'])

			if debug_mode:
				print_board(board)
				print(fen)
				print(get_pgn(move_history))
				print(f"[GAME #{len(pgns)+1}][LICHESS {move_number+1}]{pgn_move_number}{dots}{lichess_move['move_san']}, fen={board.fen()}, play%={round(100*lichess_move['percentage_played'],1)}%, previous_play%={round(100*previous_percentage_played_previous,1)}%")

			run_game_lines(engine, human_engine, board, move_history, pgns, last_lichess_total, stockfish_turn, threshold, debug_mode=debug_mode, skip_lichess=skip_lichess, stockfish_timeout=stockfish_timeout, fen_cache=fen_cache)
			board.pop()
			move_history.pop()
	else:
		if "mate" in move_history[-1]:
			move = stockfish17.analyze_board(engine, board, stockfish_timeout)
			board.push_san(move['san']);
			move_history.append(move['san'])

		else:
			result = human_engine.play(board, chess.engine.Limit(depth=100, time=1))
			move = board.san(result.move)
			move_history.append(move)
			board.push_san(move)

		if debug_mode:
			print_board(board)
			print(fen)
			print(get_pgn(move_history))
			# print(f"[GAME #{len(pgns)+1}][AICHESSJS]{pgn_move_number}{dots}{json_output['san']}, fen={board.fen()}")
			print(f"[GAME #{len(pgns)+1}][FAKEHUMAN]{pgn_move_number}{dots}{move}, fen={board.fen()}")

		run_game_lines(engine, human_engine, board, move_history, pgns, last_lichess_total, stockfish_turn, threshold, debug_mode=debug_mode, skip_lichess=skip_lichess, stockfish_timeout=stockfish_timeout, fen_cache=fen_cache)
		board.pop()
		move_history.pop()

	board.pop()
	move_history.pop()
	return

def read_file(filename):
	content = []
	with open(filename, "r") as file_buffer:
		for line in file_buffer.readlines():
			content.append(line.strip())
	return content

def load_initial_move_history(move_history_input):
	move_history = []
	if move_history_input != None:	
		move_history  = re.split("[, ]+", re.sub("[0-9]+\\. *", "", move_history_input))

	return move_history

def remove_comment(line):
	return re.sub("\{[^}]+\}", "", line)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog="run_game", description="Simulations of chess games between Stockfish and common human openings", epilog="Written by binary.initials, 01")
	parser.add_argument('-t', '--turn', help="[REQUIRED] Turn")
	parser.add_argument('-m', '--move-history', help="[REQUIRED] Move history, e.g. 'e4 e5 Nf3 Nc6'")
	parser.add_argument('-p', '--threshold', default=0.5, type=float, help="[OPTIONAL] Evaluate moves with a play rate greater than this threshold (0.0=evaluates everything, 1.0=evaluates the most popular move)")
	parser.add_argument('-d', '--debug-mode', default=False, type=bool, help="[OPTIONAL] Debug mode")
	parser.add_argument('-s', '--skip-lichess', default=False, type=bool, help="[OPTIONAL] Skip lichess")
	parser.add_argument('-f', '--filename', help="[REQUIRED] Output filename")
	parser.add_argument('--stockfish-timeout', default=DEFAULT_STOCKFISH_TIMEOUT, type=float, help="[OPTIONAL] Stockfish timeout")
	parser.add_argument('--previous-cache-file', help="[OPTIONAL] Previous file to get cache from")
	
	args = parser.parse_args()
	turn = args.turn
	move_history_input = args.move_history
	debug_mode = args.debug_mode
	threshold = args.threshold
	skip_lichess = args.skip_lichess
	filename = args.filename

	stockfish_timeout = args.stockfish_timeout
	
	if threshold > 1 or threshold < 0:
		print("[ERROR] Max play threshold rate argument must be a decimal between [0-1]")
		exit()

	if turn.lower() not in ["w", "white", "b", "black"]:
		print("[ERROR] Invalid turn argument")
		exit()

	filename += f"_{timestamp(datetime.datetime.now())}.txt"
	turn = turn.lower()[0]

	fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
	initial_move_history = []

	lines_to_output = []
	pgn_cache = []

	pgns = []
	board = chess.Board()
	initial_move_history = load_initial_move_history(move_history_input)
	for move in initial_move_history:
		board.push_san(move)

	if debug_mode:
		print(f"[DEBUG] Stockfish team: {turn}")
		print("[DEBUG] Starting board state:")
		print_board(board)
		print(f"[DEBUG][fen]\t{board.fen()}")

	fen_cache = []
	if args.previous_cache_file != None:
		file_content = read_file(args.previous_cache_file)
		for pgn in file_content:
			check_board = chess.Board()
			clean_line = remove_comment(pgn)
			moves = re.split("[, ]+", re.sub("[0-9]+\\. *", "", clean_line))
			for move_san in moves:
				check_board.push_san(move_san)
				fen_cache.append(check_board.fen().split(" ")[0])

	tic = timer()
	engine = stockfish17.initialize_engine(options={"Threads": 16})
	engine_human = stockfish17.initialize_engine(options={"UCI_LimitStrength": True, "UCI_Elo": 2500})

	run_game_lines(engine=engine, human_engine=engine_human, board=board, move_history=initial_move_history, pgns=pgns, last_lichess_total=1_000_000_000_000, stockfish_turn=turn, debug_mode=debug_mode, threshold=threshold, skip_lichess=skip_lichess, stockfish_timeout=stockfish_timeout, fen_cache=fen_cache)
	stockfish17.close_engine(engine)
	stockfish17.close_engine(engine_human)
	delta_time = dt(tic)
	print(f"dt={delta_time}, average time/game={delta_time/len(pgns)}")
	print()
	for pgn in pgns:
		pgn_cache.append(pgn)
		lines_to_output.append(pgn)

	write_to_file(filename, lines_to_output)