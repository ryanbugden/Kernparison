<img src="source/resources/mechanic_icon.png"  width="80">

# Kernparison
A RoboFont extension for comparing how you kerned the current pair across your whole Designspace.

![](source/resources/ui-main.png)

## Functionality

- Ability to view how kerning pairs were handled across all sources in a given designspace.
- An auto-updating preview.
	- As window is resized, Kernparison will make the most optimal layout for maximum visibility.
	- As you kern in Metrics Machine, Kernparison, will show that active pair. If the UFO you’re working on is one of the sources in Kernparison, it will update as you kern it.
	- Positive kerns are green. Negative kerns are red. 0 is neutral.
- Double-click a cell to open that UFO.
- Uses the current designspace you have open in Designspace Editor. If you don’t have a designspace open already, and if you don’t already have a designspace linked to your UFO (with [Designspace Manager](https://github.com/ryanbugden/Designspace-Manager) or simply using `font.lib['public.designspaces']`. Kernparison will prompt you to choose a path to a designspace file.


© Ryan Bugden, 2025

## Acknowledgments

- Hannes Famira, for the idea behind this extension, and the initial sponsorship for its development.
- Built with RoboFont, EZUI, Merz, Subscriber. Thank you to Frederik Berlaen & Tal Leming.
