"""The 20-Watt Computer, episode 1: "A bag of parts" (neuron types). Manim Community v0.21.

Each narration segment (audio/<name>.wav) drives one visual block; the block's animations are scaled to the
segment's duration (durations.json), so picture and voice stay in step.
"""
import json, random
from manim import *

HERE = "/w/ep01/"
DUR = json.load(open(HERE + "durations.json"))
BG = "#10161D"; INK = "#E4E9EF"; MUTED = "#93A1B1"; LINE = "#2E3C4B"
GLUT_C = "#86ACEA"; GABA_C = "#F08C7F"; SPIKE = "#F2C14E"; OTHER = "#B7E4A8"
config.background_color = BG
FONT = "DejaVu Sans"


def T(s, size=36, color=INK, weight=NORMAL):
    return Text(s, font=FONT, font_size=size, color=color, weight=weight)


class Episode01(Scene):
    def seg(self, name):
        """Start a narration segment; returns its duration in seconds."""
        self.add_sound(HERE + f"audio/{name}.wav")
        with open(HERE + "starts.txt", "a") as f:
            f.write(f"{name} {self.renderer.time:.3f}\n")
        return DUR[name]

    def finish(self, used, total, *fade):
        rest = max(0.2, total - used - 0.6)
        self.wait(rest)
        if fade:
            self.play(*[FadeOut(m) for m in fade], run_time=0.6)

    def construct(self):
        self.hook(); self.bag(); self.neuron(); self.sort(); self.counts()
        self.radio(); self.lock(); self.dopamine(); self.outro()

    # 1. 20 W vs 700 W
    def hook(self):
        d = self.seg("hook")
        title = T("Your brain runs on 20 watts", 48, weight=BOLD).to_edge(UP, buff=0.8)
        base = Line(LEFT * 4.5, RIGHT * 4.5, color=LINE).shift(DOWN * 2.2)
        brain = Rectangle(width=1.6, height=20 / 700 * 4.2, color=SPIKE, fill_opacity=1).next_to(base, UP, buff=0).shift(LEFT * 2)
        gpu = Rectangle(width=1.6, height=4.2, color=MUTED, fill_opacity=0.9).next_to(base, UP, buff=0).shift(RIGHT * 2)
        lb = T("brain  20 W", 30, SPIKE).next_to(brain, DOWN, buff=0.3)
        lg = T("AI accelerator  700 W", 30, MUTED).next_to(gpu, DOWN, buff=0.3)
        self.play(Write(title), run_time=1.5)
        self.play(Create(base), GrowFromEdge(brain, DOWN), FadeIn(lb), run_time=1.5)
        self.play(GrowFromEdge(gpu, DOWN), FadeIn(lg), run_time=2.5)
        self.finish(5.5, d, title, base, brain, gpu, lb, lg)

    # 2. A bag of 86 billion parts
    def bag(self):
        d = self.seg("bag")
        random.seed(1)
        dots = VGroup(*[Dot(radius=0.06, color=GLUT_C) for _ in range(400)])
        dots.arrange_in_grid(20, 20, buff=0.14).scale(1.1)
        count = T("86 000 000 000 parts", 40, weight=BOLD).to_edge(UP, buff=0.6)
        self.play(FadeIn(count), LaggedStart(*[FadeIn(x, scale=0.3) for x in dots], lag_ratio=0.004), run_time=3)
        qs = VGroup(T("inputs?", 34, SPIKE), T("outputs?", 34, SPIKE), T("what does it put out?", 34, SPIKE)).arrange(DOWN, buff=0.4)
        qs.to_edge(RIGHT, buff=0.7)
        self.play(dots.animate.shift(LEFT * 2.2), run_time=1)
        for q in qs:
            self.play(FadeIn(q, shift=LEFT * 0.3), run_time=0.8)
        self.finish(3 + 1 + 2.4, d, dots, count, qs)

    # 3. The neuron: many in, one out (branching), threshold, clicks
    def neuron(self):
        d = self.seg("neuron")
        soma = Circle(radius=0.55, color=GLUT_C, fill_opacity=0.25).shift(LEFT * 1)
        ins = VGroup(*[Line(LEFT * 5.8 + UP * y, soma.get_left() + UP * y * 0.15, color=MUTED, stroke_width=2) for y in [-2.4, -1.6, -0.8, 0, 0.8, 1.6, 2.4]])
        axon = Line(soma.get_right(), RIGHT * 2.2, color=GLUT_C, stroke_width=4)
        branches = VGroup(*[Line(RIGHT * 2.2, RIGHT * 4.6 + UP * y, color=GLUT_C, stroke_width=2) for y in [-2, -1, 0, 1, 2]])
        self.play(LaggedStart(*[Create(l) for l in ins], lag_ratio=0.1), FadeIn(soma), run_time=2.5)
        self.play(Create(axon), LaggedStart(*[Create(b) for b in branches], lag_ratio=0.1), run_time=2)
        # summation meter
        meter = Rectangle(width=0.35, height=2.2, color=INK).next_to(soma, UP, buff=0.35)
        thr = DashedLine(meter.get_corner(UL) + DOWN * 0.5 + LEFT * 0.3, meter.get_corner(UR) + DOWN * 0.5 + RIGHT * 0.3, color=SPIKE)
        level = ValueTracker(0.1)
        fill = always_redraw(lambda: Rectangle(width=0.33, height=max(0.01, 2.2 * level.get_value()), color=GLUT_C, fill_opacity=0.9, stroke_width=0).align_to(meter, DOWN).move_to(meter.get_bottom(), aligned_edge=DOWN))
        tl = T("threshold", 22, SPIKE).next_to(thr, RIGHT, buff=0.15)
        self.play(Create(meter), Create(thr), FadeIn(tl), run_time=1)
        self.add(fill)
        self.play(level.animate.set_value(0.45), run_time=1.2)
        self.play(level.animate.set_value(0.3), run_time=0.8)
        self.play(level.animate.set_value(0.8), run_time=1.2)
        flash = Flash(soma, color=SPIKE, line_length=0.4, flash_radius=0.8)
        pulses = [Dot(color=SPIKE, radius=0.08).move_to(RIGHT * 2.2) for _ in branches]
        self.play(flash, level.animate.set_value(0.05), run_time=0.8)
        self.play(*[MoveAlongPath(p, b) for p, b in zip(pulses, branches)], run_time=1.2)
        self.remove(*pulses)
        # the click train: timing carries the message
        axis = Line(LEFT * 5.5, RIGHT * 5.5, color=LINE).shift(DOWN * 3.2)
        ticks = VGroup(*[Line(axis.point_from_proportion(p), axis.point_from_proportion(p) + UP * 0.5, color=SPIKE, stroke_width=4)
                         for p in [0.05, 0.11, 0.3, 0.33, 0.36, 0.6, 0.83, 0.9]])
        cap = T("every click is the same: the message is in the timing", 26, MUTED).next_to(axis, UP, buff=0.7)
        self.play(Create(axis), LaggedStart(*[Create(t) for t in ticks], lag_ratio=0.2), FadeIn(cap), run_time=2.5)
        self.finish(2.5 + 2 + 1 + 3.2 + 0.8 + 1.2 + 2.5, d, soma, ins, axon, branches, meter, thr, tl, fill, axis, ticks, cap)

    # 4. Sort by transmitter: four-letter codes
    def sort(self):
        d = self.seg("sort")
        a = Circle(radius=0.35, color=GLUT_C, fill_opacity=0.3).shift(LEFT * 3 + UP * 1.5)
        b = Circle(radius=0.35, color=MUTED, fill_opacity=0.3).shift(LEFT * 0.4 + UP * 1.5)
        gap = T("gap", 22, MUTED).move_to((a.get_right() + b.get_left()) / 2 + UP * 0.55)
        mols = VGroup(*[Dot(radius=0.05, color=SPIKE) for _ in range(6)])
        for i, m in enumerate(mols):
            m.move_to(a.get_right() + RIGHT * 0.1 + UP * (0.25 - 0.1 * i))
        self.play(FadeIn(a), FadeIn(b), FadeIn(gap), run_time=1.2)
        self.play(*[m.animate.shift(RIGHT * 1.4) for m in mols], FadeIn(mols), run_time=1.8)
        codes = [("GLUT", "glutamate", GLUT_C), ("GABA", "GABA", GABA_C), ("DOPA", "dopamine", OTHER), ("SERO", "serotonin", OTHER),
                 ("NORA", "noradrenaline", OTHER), ("ACET", "acetylcholine", OTHER)]
        chips = VGroup()
        for code, name, col in codes:
            box = RoundedRectangle(corner_radius=0.12, width=2.1, height=0.7, color=col, fill_opacity=0.15)
            g = VGroup(box, T(code, 30, col, BOLD).move_to(box), T(name, 20, MUTED).next_to(box, DOWN, buff=0.12))
            chips.add(g)
        chips.arrange_in_grid(2, 3, buff=(0.5, 0.6)).shift(DOWN * 1.2)
        self.play(FadeOut(mols), run_time=0.4)
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in chips], lag_ratio=0.35), run_time=4)
        self.finish(1.2 + 1.8 + 0.4 + 4, d, a, b, gap, chips)

    # 5. 960 / 36 / a few in 100 000
    def counts(self):
        d = self.seg("counts")
        dots = VGroup(*[Dot(radius=0.07, color=GLUT_C) for _ in range(1000)]).arrange_in_grid(25, 40, buff=0.1).scale(0.95).shift(UP * 0.3)
        self.play(FadeIn(dots), run_time=1.2)
        red = dots[-36:]
        self.play(*[x.animate.set_color(GABA_C) for x in red], run_time=1.5)
        leg = VGroup(T("960  GLUT  (+)", 30, GLUT_C), T("36  GABA  (−)", 30, GABA_C),
                     T("all the others: a few in 100 000", 30, OTHER)).arrange(RIGHT, buff=0.7).to_edge(DOWN, buff=0.5)
        self.play(LaggedStart(*[FadeIn(l) for l in leg], lag_ratio=0.6), run_time=3)
        self.finish(1.2 + 1.5 + 3, d, dots, leg)

    # 6. Telephone lines vs radio stations
    def radio(self):
        d = self.seg("radio")
        random.seed(3)
        pts = [np.array([random.uniform(-6, 6), random.uniform(-3, 2.6), 0]) for _ in range(60)]
        cells = VGroup(*[Dot(p, radius=0.06, color=MUTED) for p in pts])
        wires = VGroup(*[Line(pts[i], pts[(i * 7 + 3) % 60], color=GLUT_C, stroke_width=1.5, stroke_opacity=0.7) for i in range(0, 60, 2)])
        lab1 = T("telephone lines: data", 32, GLUT_C).to_edge(UP, buff=0.4)
        self.play(FadeIn(cells), run_time=1)
        self.play(LaggedStart(*[Create(w) for w in wires], lag_ratio=0.05), FadeIn(lab1), run_time=3)
        station = Dot(ORIGIN + DOWN * 0.2, radius=0.14, color=SPIKE)
        lab2 = T("radio stations: settings", 32, SPIKE).to_edge(UP, buff=0.4)
        self.play(wires.animate.set_stroke(opacity=0.2), FadeIn(station), ReplacementTransform(lab1, lab2), run_time=1.2)
        for _ in range(3):
            ring = Circle(radius=0.2, color=SPIKE, stroke_width=3).move_to(station)
            self.play(ring.animate.scale(40).set_stroke(opacity=0), cells.animate.set_color(SPIKE), run_time=1.6)
            self.play(cells.animate.set_color(MUTED), run_time=0.3)
        regs = T("billions of memory cells  +  a handful of control registers", 28, INK).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(regs), run_time=1)
        self.finish(1 + 3 + 1.2 + 5.7 + 1, d, cells, wires, station, lab2, regs)

    # 7. The key and the lock
    def lock(self):
        d = self.seg("lock")
        key = VGroup(Circle(radius=0.3, color=SPIKE, fill_opacity=0.3), Rectangle(width=1.1, height=0.18, color=SPIKE, fill_opacity=0.6).shift(RIGHT * 0.8)).shift(UP * 0.2)
        kl = T("dopamine", 26, SPIKE).next_to(key, UP, buff=0.3)
        c1 = VGroup(RoundedRectangle(width=2.6, height=1.6, corner_radius=0.2, color=GLUT_C), T("lock D1:  +", 28, GLUT_C)).shift(RIGHT * 3.6 + UP * 1.4)
        c2 = VGroup(RoundedRectangle(width=2.6, height=1.6, corner_radius=0.2, color=GABA_C), T("lock D2:  −", 28, GABA_C)).shift(RIGHT * 3.6 + DOWN * 1.4)
        c1[1].move_to(c1[0]); c2[1].move_to(c2[0])
        g = VGroup(key, kl).shift(LEFT * 3)
        self.play(FadeIn(g), FadeIn(c1), FadeIn(c2), run_time=1.5)
        k2 = g.copy()
        self.play(g.animate.next_to(c1, LEFT, buff=0.1), k2.animate.next_to(c2, LEFT, buff=0.1), run_time=2)
        self.play(Indicate(c1, color=GLUT_C), Indicate(c2, color=GABA_C), run_time=1.5)
        cap = T("the receiver decides the sign", 32, INK).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(cap), run_time=0.8)
        self.finish(1.5 + 2 + 1.5 + 0.8, d, g, k2, c1, c2, cap)

    # 8. Dopamine: better than expected
    def dopamine(self):
        d = self.seg("dopamine")
        rows = []
        labels = ["juice, no lamp", "lamp, then juice", "lamp, no juice"]
        for i, lab in enumerate(labels):
            y = 2 - i * 2
            axis = Line(LEFT * 3, RIGHT * 5.5, color=LINE).shift(UP * y)
            t = T(lab, 26, MUTED).next_to(axis, LEFT, buff=0.3)
            rows.append((axis, t, y))
        self.play(*[FadeIn(VGroup(a, t)) for a, t, _ in rows], run_time=1.2)
        base_ticks = [-2.6, -2.1, -1.2, -0.6, 0.2, 0.9, 1.6, 2.3, 3.0, 3.8, 4.5, 5.1]

        def train(y, burst_at=None, gap=None):
            g = VGroup()
            for x in base_ticks:
                if gap and gap[0] < x < gap[1]:
                    continue
                g.add(Line([x, y, 0], [x, y + 0.35, 0], color=MUTED, stroke_width=3))
            if burst_at is not None:
                for k in range(5):
                    g.add(Line([burst_at + k * 0.09, y, 0], [burst_at + k * 0.09, y + 0.7, 0], color=SPIKE, stroke_width=4))
            return g
        juice_x, lamp_x = 2.6, -0.2
        juice = lambda y: VGroup(Dot([juice_x + 0.2, y + 1.0, 0], color=GLUT_C), T("juice", 20, GLUT_C).move_to([juice_x + 0.2, y + 1.35, 0]))
        lamp = lambda y: VGroup(Star(n=6, outer_radius=0.16, color=SPIKE, fill_opacity=1).move_to([lamp_x + 0.2, y + 1.0, 0]), T("lamp", 20, SPIKE).move_to([lamp_x + 0.2, y + 1.35, 0]))
        y0, y1, y2 = rows[0][2], rows[1][2], rows[2][2]
        r0 = VGroup(train(y0, burst_at=juice_x), juice(y0))
        self.play(FadeIn(r0), run_time=3)
        r1 = VGroup(train(y1, burst_at=lamp_x), lamp(y1), juice(y1))
        self.play(FadeIn(r1), run_time=4)
        r2 = VGroup(train(y2, burst_at=lamp_x, gap=(juice_x - 0.4, juice_x + 0.9)), lamp(y2))
        dip = T("silence", 22, GABA_C).move_to([juice_x + 0.25, y2 - 0.35, 0])
        self.play(FadeIn(r2), FadeIn(dip), run_time=4)
        msg = T("dopamine = better than expected", 38, SPIKE, BOLD).to_edge(DOWN, buff=0.25)
        self.play(Write(msg), run_time=1.5)
        self.finish(1.2 + 3 + 4 + 4 + 1.5, d, *[VGroup(a, t) for a, t, _ in rows], r0, r1, r2, dip, msg)

    # 9. Outro
    def outro(self):
        d = self.seg("outro")
        t1 = T("The 20-Watt Computer", 54, INK, BOLD).shift(UP * 1.6)
        t2 = T("free book · many languages · runnable models", 30, MUTED).next_to(t1, DOWN, buff=0.4)
        url = T("kladkogex.github.io/20-watt-computer", 34, SPIKE).next_to(t2, DOWN, buff=0.8)
        star = T("★ star it on GitHub", 32, INK).next_to(url, DOWN, buff=0.5)
        nxt = T("next: what can you build from pluses alone?", 28, GLUT_C).to_edge(DOWN, buff=0.6)
        self.play(Write(t1), run_time=1.5)
        self.play(FadeIn(t2), FadeIn(url), run_time=1.2)
        self.play(FadeIn(star), FadeIn(nxt), run_time=1)
        self.wait(max(0.5, d - 3.7))
