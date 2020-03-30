# not used atm, this will broke cross platform compatibility.
# this should be implemented in Toga. 

def option_enabled(container, index, value):
    tabview = container._impl.native.tabViewItemAtIndex(index)
    tabview._setTabEnabled(value)