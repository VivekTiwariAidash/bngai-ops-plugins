def classFactory(iface):
    from .spike_checker import SpikeCheckerPlugin
    return SpikeCheckerPlugin(iface)
