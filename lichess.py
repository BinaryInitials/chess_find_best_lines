import chess
import datetime
import json
import re
import requests
import subprocess
import time
import urllib.parse

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
SPEEDS="blitz,rapid,bullet,ultraBullet,classical,correspondence"
# RATINGS="1000,1200,1400,1600,1800,2000,2200,2500"
# I am not playing against grand masters
RATINGS="1000,1200,1400,1600,1800,2000"
STARTING_FEN="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def curl(url, payload, user_agent):
	headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8', 'User-Agent': f"{user_agent}"}
	r = requests.get(url + payload, headers=headers)
	json_object = {}
	try:
		json_object = r.json()
	except JSONDecodeError as e:
		print(e)
		time.sleep(10)
		r = requests.get(url + payload, headers=headers)
		json_object = r.json()

	return json_object

def get_lichess_data(opening_moves=[], is_uci=False):
	openings_moves_without_comments = []
	for opening_move in opening_moves:
		opening_move_without_comments = re.sub("\{[^}]+\}", "", opening_move)
		openings_moves_without_comments.append(opening_move_without_comments)
	opening_moves_lichess = ""
	if is_uci:
		opening_moves_lichess = ",".join(openings_moves_without_comments)

	# Default behavior:
	else:
		opening_moves_lichess = ",".join(convert_moves_from_san_to_uci(openings_moves_without_comments))

	url = "https://explorer.lichess.ovh/lichess?"
	now = datetime.datetime.now()
	until = f"{now.year}-{now.month}"
	payload = urllib.parse.urlencode({"variant": "standard", "fen": STARTING_FEN, "play": opening_moves_lichess, "until": until, "speeds": SPEEDS, "ratings": RATINGS})
	return process_lichess_data(curl(url, payload, USER_AGENT))

def convert_moves_from_san_to_uci(moves_san, is_lichess=True):
	board = chess.Board(STARTING_FEN)
	opening_moves_uci = []
	for move_san_of_interest in moves_san:
		moves = list(board.generate_legal_moves())
		for move in moves:
			move_san = board.san(move)
			if move_san == move_san_of_interest:
				move_uci_to_store = move.uci()

				if is_lichess:
					if "O-O" == move_uci_to_store: 
						move_uci_to_store = re.sub("e([18])g([18])", "e\\1h\\2", move_uci_to_store)
					elif "O-O-O" == move_uci_to_store: 
						move_uci_to_store = re.sub("e([18])c([18])", "e\\1a\\2", move_uci_to_store)
				opening_moves_uci.append(move_uci_to_store)
				board.push(move)
				break
	return opening_moves_uci

def process_lichess_data(json_data):
	parent_white_wins = json_data["white"]
	parent_black_wins = json_data["black"]
	parent_draws = json_data["draws"]
	total = parent_white_wins + parent_black_wins + parent_draws
	if total == 0:
		return {"total": 0, "moves": []}

	average_parent_white_wins = parent_white_wins / total
	average_parent_black_wins = parent_black_wins / total
	rank = 0
	accumulated_percentage = 0
	lichess_object = {"total": total}
	lichess_moves = []
	for move in json_data["moves"]:
		rank += 1
		uci = move["uci"]
		san = move["san"]
		rating_avg = move["averageRating"]
		white_wins = move["white"]
		black_wins = move["black"]
		draws_wins = move["draws"]
		move_total = white_wins + black_wins  + draws_wins

		average_move_wins = 0
		percentage_played = move_total / total
		accumulated_percentage += percentage_played
		lichess_moves.append({"rank": rank, "move_uci": uci, "move_san": san, "rating_avg": rating_avg, "move_total": move_total, "white": white_wins, "black": black_wins, "white_pct": white_wins/move_total, "black_pct": black_wins/move_total, "percentage_played": percentage_played, "parent_white_pct": average_parent_white_wins, "parent_black_pct": average_parent_black_wins, "total_played": total})
	lichess_object["moves"] = lichess_moves
	return lichess_object