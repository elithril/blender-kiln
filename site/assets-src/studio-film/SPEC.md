GOAL:    a developer sees that in Kiln Studio you pin a note on the model and Claude changes the model — and believes it,
         because every screen and number is from one real session.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps, silent
TIME:    37 s x 30 = 1110 frames
LOOK:    three worlds, each the medium's own:
         - Studio: its real UI, captured at 3840x2160 on the GPU; ground #0B0D11, panels #10141C/#141924, ink #E6EBF2,
           muted #A3ADBE, accent #5CE1E6 (Studio's own) — the accent only on the pin, the "Work on it with Claude"
           button, the ADDRESSED stamp and one word per title.
         - Claude's Blender: Blender's grey viewport #3D3D3D with #2B2B2B panels; the session's own `look` views
           (644 px, shown at <= 1.45x in a 4 px #1F1F1F frame, 10 px radius); Claude's lines in JetBrains Mono 30 px #E6EBF2.
         - The forge sweep: the mascot rendered in Blender on a warm seamless sweep (#D9C6AD floor, #F2E6D6 world),
           ink #2A1D14, accent #E8742C (the mascot's hair) for the end card.
         Type: Sora 700 for titles, 64-84 px, tracking -1.5%; Sora 400 for secondary lines, 30-36 px; JetBrains Mono 26-30 px
         for code, labels and numbers. Shadows on carried cards: 0 24px 60px rgba(0,0,0,.45). No grain, no vignette.
OBJECTS: the cursor (macOS arrow, white with 2 px black outline, 64 px tall = 6% of the frame);
         the pin (Studio's: a teal #5CE1E6 disc 34 px with its number in #062A2C, a white ring, a short stem);
         the note card (Studio's: #141924, 1 px #2A3345 border, OPEN chip amber #F5B342 / ADDRESSED chip teal, the
         object line in JetBrains Mono #808A9D, the note text in Sora 400 #E6EBF2) at 1.8x;
         the "Work on it with Claude" button (teal fill, #062A2C label, 8 px radius) at 2.2x;
         the mascot (orange hair, blue shirt, leather apron, the hammer) — never redrawn, only captured or rendered.
MOTION:  enter expo.out 0.5-0.7 s; camera power2.inOut 0.6-0.8 s; exits power3.in 0.3 s; carry-across 0.7 s with 6 px
         blur peak; typing 32 ms a character; title words per word blur 6->0 + opacity, 80 ms apart, no translate;
         numbers count over 0.6 s power2.out; springs only on the pin drop (back.out(1.6), position only).
SHOTS:   (frames at 30 fps)
  01 0-120     Studio, the mascot (s1-model), push 1.0 -> 1.55 onto the hammer (0.6-1.4 s); the cursor enters from the
               right (1.0 s), lands on the hammer, clicks at 2.3 s: the pin drops on the click frame. Reads: the model
               (0-1 s), the hammer (1-2.3 s). Hands off: the pin.
  02 120-270   the composer grows out of the pin (morph 0.4 s) at 1.8x beside the hammer; the note types (4.4-7.4 s);
               "Save note" clicked 7.8 s -> the card becomes the OPEN note card. Reads: the note text (4.4-8.6 s).
  03 270-360   the note card slides to the panel; "Work on it with Claude" pushes in to 2.2x; cursor clicks at 10.2 s;
               the button's teal fill grows past the frame (0.65 s) — object becomes the world. Title (10.6-12 s):
               "Claude takes the note".
  04 360-720   Claude's Blender. The note card, carried in small, top left; four real steps, 3 s each, one per line,
               each with its evidence: (a) "Before scaling, a look from the note's angle." + look-1;
               (b) "Hammer: 0.35 → 0.52 m long" (count) ; (c) "The hammer passes through the leg: 17 of 66 frames"
               + look-2, then "A 20° wrist twist clears every frame → 0" + look-3; (d) "0 errors, 0 warnings" +
               "Re-exported · 368 KB". A thin progress line along the bottom fills over the shot, labelled
               "4 min of work · $1.63 · shown 20× faster".
  05 720-900   back to Studio (s5-after): the note card lands in the panel, the chip flips OPEN -> ADDRESSED, the reply
               bullets reveal (0.35 m → 0.52 m highlighted); push onto the bigger hammer; then zoom through the
               AFTER thumbnail into the forge sweep.
  06 900-1000  the mascot walks with the bigger hammer, full frame, normal speed (2 loops of 2.17 s). Title on the
               left third, per word: "Pin a note." / "Claude fixes it." (accent on "fixes").
  07 1000-1110 end card on the sweep: the kiln forge mark carried up into the centre (lockup 22% of the width),
               "Kiln Studio" wipes in beside it, then `/kiln studio` in a real-looking command field; footnote
               "Real session, re-cut · blender-kiln 3.0" in Sora 400 26 px #6B5A4C. Holds 2.2 s.
BANNED:  the defaults of spec.md; plus: any UI element not in the captures; any number not in BRIEF.md § Facts;
         product UI tilted in 3D; floating cards in an empty void; click rings; a title over a dimmed screenshot;
         the logo docked in a corner; the Studio ground used outside the Studio shots.
QA:      0.0 s (frame 0 is a real Studio frame, not black); 2.3 s (pin on the click frame); 6.0 s (note mid-typing,
         legible >= 28 px); 10.2 s (click on the button); 13 s, 16 s, 19 s, 22 s (each step: line + evidence); 25 s
         (ADDRESSED + reply legible); 28 s (walk, hammer clear of the leg); 32 s (title); 36 s (end card).
