"""Toy model for the DishBrain chapter: can "noise on a miss, quiet on a hit" teach Pong
without any reward signal? Pure Python.

The culture is reduced to two numbers theta = (a, b): the paddle goes to p = clip(a*y + b, 0, 1)
when the ball arrives at height y (uniform on [0,1]); a hit if |p - y| < h.
Feedback conditions, as in the experiment:
  stimulus  : after a miss the parameters get a random kick (unpredictable stimulation scrambles
              recent changes); after a hit nothing changes (predictable stimulation).
  noise_all : a random kick after every rally (no information in the feedback).
  silent    : no kicks at all.
Prints the mean hit rate in the first 200 and the last 500 rallies over many cultures.
"""
import random

def run(cond, rallies=2000, h=0.1, sigma=0.08, seed=0):
    rnd = random.Random(seed)
    a, b = rnd.uniform(-1, 1), rnd.uniform(0, 1)
    hits = []
    for _ in range(rallies):
        y = rnd.random()
        p = min(1.0, max(0.0, a * y + b))
        hit = abs(p - y) < h
        hits.append(hit)
        kick = (cond == "stimulus" and not hit) or cond == "noise_all"
        if kick:
            a += rnd.gauss(0, sigma); b += rnd.gauss(0, sigma)
    return hits

if __name__ == "__main__":
    n = 40
    for cond in ("stimulus", "noise_all", "silent"):
        first = last = 0.0
        for s in range(n):
            hs = run(cond, seed=s)
            first += sum(hs[:200]) / 200 / n
            last += sum(hs[-500:]) / 500 / n
        print(f"{cond:9s}: hit rate first 200 = {first:.2f}, last 500 = {last:.2f}")
