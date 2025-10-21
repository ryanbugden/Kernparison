<img src="source/resources/mechanic_icon.png"  width="80">

# Kernparison
A RoboFont extension for comparing how you kerned the current pair across your whole Designspace.

© Ryan Bugden, 2025

![](source/resources/ui-main.png)

## Functionality

- Ability to view how kerning pairs were handled across all sources in a given designspace.
- An auto-updating preview.
	- As window is resized, Kernparison will make the most optimal layout for maximum visibility.
	- As you kern in Metrics Machine, Kernparison, will show that active pair. If the UFO you’re working on is one of the sources in Kernparison, it will update as you kern it.
	- Positive kerns are green. Negative kerns are red. 0 is neutral.
- Double-click a cell to open that UFO.
- Kernparison will try to open a designspace in this order:
	1. The current designspace you have open in Designspace Editor. 
	2. The first designspace linked to your UFO (with [Designspace Manager](https://github.com/ryanbugden/Designspace-Manager) or simply using `font.lib['public.designspaces']`. 
	3. Or it will prompt you to choose a path to a designspace file.




## Acknowledgments

- Hannes Famira, for the idea behind this extension, and the initial sponsorship for its development.
- Built with RoboFont, EZUI, Merz, Subscriber. Thank you to Frederik Berlaen & Tal Leming.
