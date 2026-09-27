"""YouTube Short (vertical 1080x1920): "Dopamine is not a pleasure signal"."""
import json
from manim import *

HERE = "/w/short01/"
DUR = json.load(open(HERE + "durations.json"))
BG = "#10161D"; INK = "#E4E9EF"; MUTED = "#93A1B1"; LINE = "#2E3C4B"; GLUT_C = "#86ACEA"; GABA_C = "#F08C7F"; SPIKE = "#F2C14E"
config.background_color = BG
config.pixel_width, config.pixel_height = 1080, 1920
config.frame_width, config.frame_height = 9, 16
FONT = "DejaVu Sans"
T = lambda s, size=44, color=INK, w=NORMAL: Text(s, font=FONT, font_size=size, color=color, weight=w)


class Short01(Scene):
    def seg(self, n):
        self.add_sound(HERE + f"audio/{n}.wav")
        return DUR[n]

    def construct(self):
        base = [-3.4, -2.9, -2.2, -1.5, -0.8, 0.0, 0.8, 1.6, 2.4, 3.2]

        def train(y, burst=None, gap=None):
            g = VGroup(Line([-3.8, y, 0], [3.8, y, 0], color=LINE))
            for x in base:
                if not (gap and gap[0] < x < gap[1]):
                    g.add(Line([x, y, 0], [x, y + 0.35, 0], color=MUTED, stroke_width=4))
            if burst is not None:
                for k in range(5):
                    g.add(Line([burst + k * 0.1, y, 0], [burst + k * 0.1, y + 0.8, 0], color=SPIKE, stroke_width=6))
            return g
        juice, lamp = 1.9, -1.2
        jmark = lambda y: VGroup(Dot([juice + 0.2, y + 1.2, 0], color=GLUT_C, radius=0.12), T("juice", 30, GLUT_C).move_to([juice + 0.2, y + 1.6, 0]))
        lmark = lambda y: VGroup(Star(n=6, outer_radius=0.2, color=SPIKE, fill_opacity=1).move_to([lamp + 0.2, y + 1.2, 0]), T("lamp", 30, SPIKE).move_to([lamp + 0.2, y + 1.6, 0]))

        d = self.seg("s1")
        title = T("Dopamine is NOT\na pleasure signal", 64, INK, BOLD).move_to(UP * 6.0)
        self.play(Write(title), run_time=1.6); self.wait(max(0.2, d - 1.6))

        d = self.seg("s2")
        r0 = VGroup(train(3.0, burst=juice), jmark(3.0)); l0 = T("surprise juice", 34, MUTED).move_to(UP * 2.35)
        self.play(FadeIn(r0), FadeIn(l0), run_time=1.5); self.wait(max(0.2, d - 1.5))

        d = self.seg("s3")
        r1 = VGroup(train(0.0, burst=lamp), lmark(0.0), jmark(0.0)); l1 = T("lamp, then juice", 34, MUTED).move_to(DOWN * 0.65)
        self.play(FadeIn(r1), FadeIn(l1), run_time=1.5); self.wait(max(0.2, d - 1.5))

        d = self.seg("s4")
        r2 = VGroup(train(-3.0, burst=lamp, gap=(juice - 0.5, juice + 1.0)), lmark(-3.0)); l2 = T("lamp, no juice", 34, MUTED).move_to(DOWN * 3.65)
        sil = T("silence", 36, GABA_C, BOLD).move_to([juice + 0.25, -2.45, 0])
        self.play(FadeIn(r2), FadeIn(l2), run_time=1.5)
        self.play(FadeIn(sil, scale=1.3), run_time=0.8); self.wait(max(0.2, d - 2.3))

        d = self.seg("s5")
        box = VGroup(T("dopamine =", 52, INK), T("better than", 64, SPIKE, BOLD), T("expected", 64, SPIKE, BOLD)).arrange(DOWN, buff=0.2).move_to(DOWN * 5.9)
        self.play(FadeIn(box, shift=UP * 0.3), run_time=1.2); self.wait(max(0.2, d - 1.2))

        d = self.seg("s6")
        self.play(*[FadeOut(m) for m in (title, r0, l0, r1, l1, r2, l2, sil, box)], run_time=0.6)
        end = VGroup(T("The 20-Watt Computer", 58, INK, BOLD), T("free book · link below", 40, SPIKE)).arrange(DOWN, buff=0.4)
        self.play(FadeIn(end), run_time=0.8); self.wait(max(0.3, d - 1.4))
