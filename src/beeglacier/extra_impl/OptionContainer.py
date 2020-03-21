def option_enabled(container, index, value):
    tabview = container._impl.native.tabViewItemAtIndex(index)
    tabview._setTabEnabled(value)