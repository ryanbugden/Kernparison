# menuTitle: Kernparison


from pathlib import Path
import unicodedata
from fontTools.misc.fixedTools import otRound
import ezui
import merz
from mojo.subscriber import Subscriber
from mojo.events import addObserver, removeObserver
from mojo.UI import Message, GetFile, inDarkMode
from glyphNameFormatter.reader import n2u
import metricsMachine as mm
from mm4.interface.documentWindow import MMDocumentWindowController


"""
Ryan Bugden
October 2025
"""


class KernparisonError(Exception):
    pass


def OpenKernparison(designspace=None):
    Kernparison = KernparisonWindowController(designspace=designspace)
    return Kernparison


def get_kern_value(f, pair):
    """Given a pair consisting of glyph names, return the kerning value."""
    return f.kerning.find(pair)


def check_exception(f, pair):
    """Given a pair consisting of glyph names, return whether it’s an exception."""
    return mm.MetricsMachineFont(f).kerning.isException(pair)


def get_kern_group(font, glyph, side):
    groups = (
        font.groups.side1KerningGroups
        if side == "left"
        else font.groups.side2KerningGroups
    )
    if glyph in groups:
        members = groups[glyph]
        if not members:
            return None
        glyph = members[0]
    for group_name, members in groups.items():
        if glyph not in members:
            continue
        return group_name
    return glyph


def convert_to_group_pair(font, pair):
    return (
        get_kern_group(font, pair[0], "left"),
        get_kern_group(font, pair[1], "right"),
    )


def open_font_in_mm(font):
    font = OpenFont(font.path, showInterface=True)

    controller = MMDocumentWindowController(font.naked())
    controller.assignToDocument(font.document())

    return font, controller


class MiniKernerPopoverController(ezui.WindowController):

    def build(self, controller, parent, font, pair, location):
        self.controller = controller
        self.parent = parent
        self.font = font
        self.pair = pair
        self.location = location

        kern_value = get_kern_value(font, pair)
        kern_value = 0 if kern_value is None else int(kern_value)

        content = """
        * HorizontalStack              @horizontalStack
        > l                            @emptyLabel1
        > * HorizontalStack
        >> [_ _]                       @kernValue
        >> (Save)                      @saveButton
        >> (Copy into Current Font)    @copyButton
        > l                            @emptyLabel2
        * MerzView                     @preview
        """

        description_data = dict(
            horizontalStack=dict(
                width="fill",
                alignment="center",
                distribution="equalCentering"
            ),
            kernValue=dict(
                value=kern_value,
                valueType="integer",
                valueIncrement=5,
                width=60,
            ),
            saveButton=dict(
                width=80
            ),
            preview=dict(
                width="fill",
                height=120,
            ),
        )
        self.w = ezui.EZPopover(
            content=content,
            descriptionData=description_data,
            parent=self.parent,
            size=(400, "auto"),
            controller=self,
        )
        self.w.getItem("saveButton").bind("\r", [])
        self.preview = self.w.getItem("preview")
        self.preview_container = self.preview.getMerzContainer()
        for identifier in ("emptyLabel1", "emptyLabel2"):
            self.w.getItem(identifier).show(False)

    def started(self):
        self.w.open(
            location=self.location,
            parentAlignment="top",
        )
        self.build_preview()

    def build_preview(self):
        self.preview_container.clearSublayers()

        preview_fill_color = (0, 0, 0, 1) if not inDarkMode() else (1, 1, 1, 1)

        left, right = self.pair
        left_unicode = n2u(left)
        right_unicode = n2u(right)
        is_lowercase = any(
            value is not None and unicodedata.category(chr(value)) == "Ll"
            for value in (left_unicode, right_unicode)
        )
        context_glyph = "n" if is_lowercase else "H"
        glyph_names = [context_glyph, context_glyph, left, right, context_glyph, context_glyph]

        preview_width, preview_height = self.preview.width(), self.preview.height()
        kern_value = get_kern_value(self.font, self.pair) or 0

        background_color = (1, 1, 1, 0)
        if kern_value < 0:
            background_color = (1, 0, 0, 0.1)
        elif kern_value > 0:
            background_color = (0, 1, 0.2, 0.1)

        self.preview_container.appendBaseSublayer(
            position=(0, 0),
            size=(preview_width, preview_height),
            backgroundColor=background_color,
            cornerRadius=8,
        )
        advances = []
        total_width = 0
        for i, glyph_name in enumerate(glyph_names):
            if glyph_name not in self.font:
                continue
            glyph = self.font[glyph_name]
            advance = glyph.width or 0
            if (
                i < len(glyph_names) - 1
                and (glyph_name, glyph_names[i + 1]) == self.pair
            ):
                advance += kern_value
            advances.append((glyph_name, advance))
            total_width += advance

        margin = 20
        if not total_width:
            return
        scale_x = (preview_width - margin * 2) / total_width
        scale_y = (preview_height - margin * 2) / self.font.info.unitsPerEm
        scale = min(scale_x, scale_y)

        x = (preview_width - total_width * scale) / 2
        baseline = (preview_height - self.font.info.capHeight * scale) / 2

        for glyph_name, advance in advances:
            glyph = self.font[glyph_name]
            path = glyph.getRepresentation("merz.CGPath")
            layer = self.preview_container.appendPathSublayer(
                fillColor=preview_fill_color,
            )
            layer.setPath(path)
            layer.addScaleTransformation(scale)
            layer.addTranslationTransformation((x / scale, baseline / scale))
            x += advance * scale

    def kernValueCallback(self, sender):
        kern_value = sender.get()
        self.font.kerning[convert_to_group_pair(self.font, self.pair)] = kern_value
        self.build_preview()

    def saveButtonCallback(self, sender):
        self.font.save()
        self.controller.build_cells()
        self.w.close()

    def copyButtonCallback(self, sender):
        kern_value = self.w.getItem("kernValue").get()
        CurrentFont().kerning[convert_to_group_pair(self.font, self.pair)] = kern_value


class KernparisonWindowController(Subscriber, ezui.WindowController):
    debug = False

    def build(self, designspace=None):
        self.designspace = designspace
        self.designspace_options = [path for path in Path(designspace.path).parent.glob("*.designspace")]
        # Load the sources of the designspace as font objects in memory
        self.fonts = [
            OpenFont(source.path, showInterface=False)
            for source in self.designspace.sources
        ]
        # Try to get the current pair from MetricsMachine on extension launch
        try:
            self.pair = mm.GetCurrentPair()
        except:
            self.pair = ("A", "V")

        content = """
        * MerzView  @gridView
        """
        descriptionData = dict(
            gridView=dict(
                backgroundColor=(1, 1, 1, 0),
                width=">=300",
                height=">=300",
                delegate=self,
            )
        )
        title = "Kernparison"

        self.w = ezui.EZWindow(
            content=content,
            descriptionData=descriptionData,
            controller=self,
            title=title,
            # margins=(0, 0, 0, 0),
            size=(500, 500),
            minSize=(400, 400),
        )
        addObserver(self, "currentPairChanged", "MetricsMachine.currentPairChanged")
        self.grid_view = self.w.getItem("gridView")
        self.grid_container = self.grid_view.getMerzContainer()
        self.grid_item_container = self.grid_container.appendBaseSublayer(
            name="gridItemContainer"
        )
        self.grid_container.setContainerScale(1.0)
        # Scales for kerning pair itself.
        # First is the desired height relative to the vertical space
        # Second is the desired width if it needs to snap smaller.
        self.scales = (0.7, 0.9)

    def started(self):
        self.w.open()
        self.build_cells()

    def destroy(self):
        removeObserver(self, "MetricsMachine.currentPairChanged")

    def windowDidResize(self, sender):
        self.build_cells()

    def currentPairChanged(self, sender):
        self.pair = sender["pair"]
        self.build_cells()

    def roboFontAppearanceChanged(self, info):
        self.build_cells()

    # Set up double-click behavior: open selected UFO
    def acceptsFirstResponder(self, sender):
        return True

    def acceptsMouseDown(self, sender):
        return True

    def _get_item_at_event(self, position):
        x, y = position
        hits = self.grid_container.findSublayersContainingPoint(
            (x, y), onlyAcceptsHit=True, recurse=True
        )
        if not hits:
            return None
        hit = hits[0]
        return hit

    def _convert_location(self, event):
        location = event["location"]
        location = self.grid_view.convertWindowCoordinateToViewCoordinate(
            point=location
        )
        x, y = self.grid_container.convertViewCoordinateToLayerCoordinate(
            location, self.grid_container
        )
        return (x, y)

    def mouseDown(self, view, event):
        self.build_cells()
        event = merz.unpackEvent(event)
        click_count = event["clickCount"]
        (x, y) = self._convert_location(event)
        hit = self._get_item_at_event((x, y))
        hit_name = hit.getName()
        if hit_name is not None:
            hit.setBorderWidth(2)
            if click_count == 2:
                i = int(hit_name)
                old_font = self.fonts[i]
                # Do nothing if this font is already the current font
                current_font = CurrentFont()
                if current_font is not None and current_font.path == old_font.path:
                    return
                # Preserve pair before MM opening fires notifications
                pair = self.pair
                new_font, controller = open_font_in_mm(old_font)
                self.fonts[i] = new_font
                if old_font is not new_font:
                    old_font.close()
                mm.SetCurrentPair(pair, font=new_font)
                # Restore internal pair reference
                self.pair = pair

    def rightMouseDown(self, view, event):
        self.build_cells()
        event = merz.unpackEvent(event)
        x, y = self._convert_location(event)
        hit = self._get_item_at_event((x, y))
        if hit is None:
            return
        hit_name = hit.getName()
        if hit_name is None:
            return
        hit.setBorderWidth(2)
        i = int(hit_name)
        font = self.fonts[i]
        x, y = hit.getPosition()
        w, h = hit.getSize()
        bottom_middle = (x + w / 2, y)
        location = (*bottom_middle, 1, 1)
        MiniKernerPopoverController(
            self,
            self.grid_view,
            font,
            self.pair,
            location,
        )

    def keyDown(self, view, event):
        """Scale the kerning pair preview up or down."""
        event = merz.unpackEvent(event)
        if event["modifiers"] != ["command"]:
            return
        char = event["character"]
        step = 0.1
        direction = -1 if char == "-" else 1
        new_scales = tuple(s + direction * step for s in self.scales)
        if all(0.1 <= s <= 0.9 for s in new_scales):
            self.scales = new_scales
            self.build_cells()

    def build_cells(self):
        """Builds/rebuilds the cells from the ground up."""
        # Calculate sizes and arrangement
        margin = 0
        gutter = 2
        font_count = len(self.fonts)
        w, h = self.grid_view.width(), self.grid_view.height()
        # aspect = w / h
        min_aspect, max_aspect = 0.5, 2
        for i in range(1, font_count + 1):
            cols = i
            rows = otRound(font_count / cols)
            if rows * cols < font_count:
                rows += 1
            # cells = rows * cols
            uw = (w - ((cols - 1) * gutter) - (margin * 2)) / cols
            uh = (h - ((rows - 1) * gutter) - (margin * 2)) / rows
            cell_aspect = uw / uh
            if min_aspect < cell_aspect < max_aspect:
                break

        # Build the cells
        self.grid_container.clearSublayers()
        i = 0
        kern_pair_sublayers = []
        width_exceeds = False
        max_pair_width = 0
        for row in range(rows):
            for col in range(cols):
                if i + 1 > font_count:
                    continue
                font = self.fonts[i]
                # Calculate slant offset, to help center slanted styles in the cell.
                slant_offset_key = "com.typemytype.robofont.italicSlantOffset"
                if slant_offset_key in font.lib.keys():
                    slant_offset = font.lib[slant_offset_key]
                else:
                    slant_offset = 0
                pair_value = get_kern_value(font, self.pair)
                black_or_white = (0, 0, 0, 1) if not inDarkMode() else (1, 1, 1, 1)
                kern_fill_color = black_or_white
                kern_bg_color = (1, 1, 1, 0)
                if pair_value is not None:
                    if pair_value < 0:
                        kern_fill_color = (1, 0, 0, 1)
                        kern_bg_color = (1, 0, 0, 0.1)
                    elif pair_value > 0:
                        kern_fill_color = (0, 170 / 255, 15 / 255, 1)
                        kern_bg_color = (0, 1, 0.2, 0.1)
                # Calculate the bottom left of each cell. Start from top left.
                x = margin + col * uw + (gutter * col)
                y = h - margin - (row + 1) * uh - (gutter * row)
                # Cell background
                self.grid_container.appendBaseSublayer(
                    position=(x, y),
                    size=(uw, uh),
                    borderColor=kern_fill_color,
                    borderWidth=0,
                    backgroundColor=kern_bg_color,
                    cornerRadius=8,
                    name=str(i),
                    acceptsHit=True,
                )
                # Style name text at the bottom
                self.grid_container.appendTextLineSublayer(
                    position=(x + uw / 2, y + 20),
                    pointSize=10,
                    fillColor=black_or_white,
                    horizontalAlignment="center",
                    text=f"{font.info.styleName}",
                    acceptsHit=False,
                )
                # Kerning value text
                kerning_value_text = str(get_kern_value(font, self.pair))
                self.grid_container.appendTextLineSublayer(
                    position=(x + uw / 2, y + 45),
                    pointSize=12,
                    weight="bold",
                    fillColor=kern_fill_color,
                    horizontalAlignment="center",
                    text=kerning_value_text,
                    acceptsHit=False,
                    borderWidth=1.5 if check_exception(font, self.pair) else 0,
                    borderColor=kern_fill_color if check_exception(font, self.pair) else (1, 1, 1, 0),
                    cornerRadius=5,
                    padding=(8, 1),
                )
                # Kerning pair drawing
                kern_pair_sublayer = self.grid_container.appendBaseSublayer(
                    position=(0, 0),
                    size=(0, 0),
                    acceptsHit=False,
                )
                x_advance = slant_offset
                pair_width = 0
                pair_i = 0
                for glyph_name in self.pair:
                    if glyph_name not in font:
                        continue
                    glyph = font[glyph_name]
                    glyph_path = glyph.getRepresentation("merz.CGPath")
                    glyph_path_layer = kern_pair_sublayer.appendPathSublayer(
                        fillColor=black_or_white,
                        acceptsHit=False,
                    )
                    glyph_path_layer.addTranslationTransformation((x_advance, 0))
                    glyph_path_layer.setPath(glyph_path)
                    glyph_width = glyph.width if glyph.width is not None else 0
                    pair_advance = (
                        pair_value if pair_value is not None and pair_i == 0 else 0
                    )
                    x_advance = glyph_width + pair_advance + slant_offset
                    pair_width += x_advance
                    pair_i += 1
                scale = uh / font.info.unitsPerEm * self.scales[0]
                if scale * pair_width > uw * self.scales[1]:
                    width_exceeds = True
                kern_pair_sublayers.append((kern_pair_sublayer, pair_width, (x, y)))
                max_pair_width = (
                    pair_width if pair_width > max_pair_width else max_pair_width
                )
                # Increment to the next font
                i += 1
        # Determine how to scale and place the kerning pair
        if width_exceeds:
            scale = uw / max_pair_width * self.scales[1]
        for kern_pair_sublayer, pair_width, (x, y) in kern_pair_sublayers:
            kern_pair_sublayer.addTranslationTransformation(
                (
                    x + (uw - scale * pair_width) / 2,
                    y + ((uh - 50) - font.info.capHeight * scale) / 2 + 50,
                )
            )
            kern_pair_sublayer.addScaleTransformation(scale)


if __name__ == "__main__":
    f = CurrentFont()
    if f is None:
        Message("Please open a UFO before launching Kernparison.")
    elif CurrentDesignspace():
        OpenKernparison(CurrentDesignspace())
    else:
        path = GetFile(
            message="Please choose a .designspace file for use with Kernparison.",
            title="Open a Designspace",
            directory=str(Path(f.path).parent),
            allowsMultipleSelection=False,
            fileTypes=["designspace"],
        )
        if path:
            designspace = OpenDesignspace(path, showInterface=False)
            OpenKernparison(designspace)
