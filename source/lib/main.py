# menuTitle: Kernparison

from random import randint 
import math
import ezui
import merz
from mojo.subscriber import Subscriber
from fontTools.misc.fixedTools import otRound
from mojo.events import addObserver, removeObserver
from mojo.UI import Message, GetFile, inDarkMode
import metricsMachine as mm


class KernparisonError(Exception): pass

def OpenKernparison(ufo_operator=None):
    Kernparison = KernparisonWindowController(ufo_operator=ufo_operator)
    return Kernparison
    
def get_kern_value(f, pair):
    '''Given a pair consisting of glyph names, return the kerning value.'''
    l, r = pair
    for group_name in f.groups.findGlyph(l):
        if "kern1" in group_name:
            l = group_name
    for group_name in f.groups.findGlyph(r):
        if "kern2" in group_name:
            r = group_name
    return f.kerning.get((l, r))
    
    
class KernparisonWindowController(Subscriber, ezui.WindowController):

    debug = False

    def build(self, ufo_operator=None):
        self.ufo_operator = ufo_operator
        # Load the sources of the designspace as font objects in memory
        self.fonts = [OpenFont(source.path, showInterface=False) for source in self.ufo_operator.sources]
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
            minSize=(500, 500)
        )
        self.grid_view = self.w.getItem("gridView")
        self.grid_container = self.grid_view.getMerzContainer()
        self.grid_item_container = self.grid_container.appendBaseSublayer(name="gridItemContainer")
        self.grid_container.setContainerScale(1.0)
        addObserver(self, 'currentPairChanged', 'MetricsMachine.currentPairChanged')
        
    def started(self):
        self.w.open()
        self.build_cells()
        
    def destroy(self):
        removeObserver(self, 'MetricsMachine.currentPairChanged')
        
    def windowDidResize(self, sender):
        self.build_cells()
        
    def currentPairChanged(self, sender):
        self.pair = sender['pair']
        self.build_cells()
        
    # Set up double-click behavior: open selected UFO
    def acceptsFirstResponder(self, sender):
        return True

    def acceptsMouseDown(self, sender):
        return True
        
    def _get_item_at_event(self, position):
        x,y = position
        hits = self.grid_container.findSublayersContainingPoint(
            (x, y),
            onlyAcceptsHit=True,
            recurse=True
        )
        if not hits:
            return None
        hit = hits[0]
        return hit

    def _convert_location(self, event):
        location = event["location"]
        location = self.grid_view.convertWindowCoordinateToViewCoordinate(point=location)
        x, y = self.grid_container.convertViewCoordinateToLayerCoordinate(location, self.grid_container)
        return (x,y)
        
    def mouseDown(self, view, event):
        self.build_cells()
        event = merz.unpackEvent(event)
        click_count = event["clickCount"]
        (x,y) = self._convert_location(event)
        hit = self._get_item_at_event((x,y))
        hit_name = hit.getName()
        if hit_name is not None:
            hit.setBorderWidth(2)
            # hit.setBackgroundColor((0,0,1,0.5))
            if click_count == 2:
                i = int(hit_name)
                # Open font
                font = self.fonts[i]
                font.openInterface()
        
    def build_cells(self):
        '''Builds/rebuilds the cells from the ground up.'''
        # Calculate sizes and arrangement
        margin = 0
        gutter = 2
        font_count = len(self.fonts)
        w, h = self.grid_view.width(), self.grid_view.height()
        aspect = w / h
        min_aspect, max_aspect = 0.5, 2
        for i in range(1, font_count + 1):
            cols = i
            rows = otRound(font_count / cols)
            if rows * cols < font_count:
                rows += 1
            cells = rows * cols
            uw = (w - ((cols-1) * gutter) - (margin*2)) / cols
            uh = (h - ((rows-1) * gutter) - (margin*2)) / rows
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
                pair_value = get_kern_value(font, self.pair)
                black_or_white = (0,0,0,1) if not inDarkMode() else (1,1,1,1)
                kern_fill_color = black_or_white
                kern_bg_color = (1,1,1,0)
                if pair_value is not None:
                    if pair_value < 0:
                        kern_fill_color = (1,0,0,1)
                        kern_bg_color = (1,0,0,0.1)
                    elif pair_value > 0:
                        kern_fill_color = (0,170/255,15/255,1)
                        kern_bg_color = (0,1,0.2,0.1)
                # Calculate the bottom left of each cell. Start from top left.
                x = margin + col*uw + (gutter * col)
                y = h - margin - (row + 1)*uh - (gutter * row)
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
                    position=(
                        x + uw/2, 
                        y + 20
                        ),
                    pointSize=10,
                    fillColor=black_or_white,
                    horizontalAlignment="center",
                    text=f"{font.info.styleName}",
                    acceptsHit=False,
                )
                # Kerning value text
                self.grid_container.appendTextLineSublayer(
                    position=(x + uw/2, y + 40),
                    pointSize=12,
                    weight="bold",
                    fillColor=kern_fill_color,
                    horizontalAlignment="center",
                    text=str(get_kern_value(font, self.pair)),
                    acceptsHit=False,
                )
                # Kerning pair drawing
                kern_pair_sublayer = self.grid_container.appendBaseSublayer(
                    position=(0, 0),
                    size=(0, 0),
                    acceptsHit=False,
                )
                x_advance = 0
                pair_width = 0
                pair_i = 0
                for glyph_name in self.pair:
                    glyph = font[glyph_name]
                    glyph_path = glyph.getRepresentation("merz.CGPath")
                    glyph_path_layer = kern_pair_sublayer.appendPathSublayer(
                        fillColor=black_or_white,
                        acceptsHit=False,
                        )            
                    glyph_path_layer.addTranslationTransformation((x_advance, 0))
                    glyph_path_layer.setPath(glyph_path)
                    glyph_width = glyph.width if glyph.width is not None else 0
                    pair_advance = pair_value if pair_value is not None and pair_i == 0 else 0
                    x_advance = glyph_width + pair_advance
                    pair_width += x_advance
                    pair_i += 1
                scale = uh/font.info.unitsPerEm * 2/3
                if scale*pair_width > uw:
                    width_exceeds = True
                kern_pair_sublayers.append((kern_pair_sublayer, pair_width, (x, y)))
                max_pair_width = pair_width if pair_width > max_pair_width else max_pair_width
                # Increment to the next font
                i += 1
        # Determine how to scale and place the kerning pair
        if width_exceeds:
            scale = uw/max_pair_width * .95
        for kern_pair_sublayer, pair_width, (x, y) in kern_pair_sublayers:
            kern_pair_sublayer.addTranslationTransformation((x + (uw-scale*pair_width)/2, y + ((uh-50) - font.info.capHeight*scale) / 2 + 50))
            kern_pair_sublayer.addScaleTransformation(scale)
        
    
if __name__ == '__main__':
    if CurrentDesignspace():
        OpenKernparison(CurrentDesignspace())
    else:
        path = GetFile(
            message="Please choose a .designspace file for use with Kernparison.", 
            title="Open a Designspace", 
            allowsMultipleSelection=False, 
            fileTypes=["designspace"]
            )
        if path:
            ufo_operator = OpenDesignspace(path, showInterface=False)
            OpenKernparison(ufo_operator)
    