"""
BNG AI Plugin Layer Management Module

This module provides a comprehensive system for managing QGIS layers related to 
BNG (Biodiversity Net Gain) calculations. The following classes are available:

- LayerManager: Core layer management functionality
- BaseLayersManager: Manager for base/existing condition layers (trees, watercourses, plans)
- BNGPlanLayersManager: Manager for BNG plan layers with biodiversity attributes
- GeometryHandler: Handler for processing GeoJSON geometries from API responses
- LayerFactory: Factory to create layers from API geometry data

Example usage:

1. Directly using layer managers:

```python
from layers import BaseLayersManager, BNGPlanLayersManager

# Create base layers
base_manager = BaseLayersManager()
tree_layer = base_manager.create_tree_layer()
watercourse_layer = base_manager.create_watercourse_layer()
plan_layer = base_manager.create_plan_layer()

# Create BNG plan layers
bng_manager = BNGPlanLayersManager()
bng_tree_layer = bng_manager.create_tree_layer()
bng_watercourse_layer = bng_manager.create_watercourse_layer()
bng_plan_layer = bng_manager.create_plan_layer()

# Calculate net gain
bng_manager.calculate_net_gain(tree_layer, bng_tree_layer)
```

2. Using with API data:

```python
from layers import LayerFactory

# Create layer factories
baseline_factory = LayerFactory(is_baseline=True)
bng_plan_factory = LayerFactory(is_baseline=False)

# Process API response data
baseline_layers = baseline_factory.process_api_response(baseline_api_data)
bng_plan_layers = bng_plan_factory.process_api_response(bng_plan_api_data)

# Calculate net gain
from layers import BNGPlanLayersManager
bng_manager = BNGPlanLayersManager()
bng_manager.calculate_net_gain(
    baseline_layers['trees'], 
    bng_plan_layers['trees']
)
```

3. Using the GUI components:

```python
from gui.map_tab import MapTab
from gui.map_data_fetcher import MapDataFetcher

# Create and use the map tab
map_tab = MapTab(auth_manager=auth_manager, api_client=api_client)
dock_widget.addTab(map_tab, "Map Data")

# Or use the data fetcher directly
data_fetcher = MapDataFetcher(api_client=api_client)
data_fetcher.fetch_baseline_data(plan_id, token, org_id)
```
"""

from .layer_manager import LayerManager
from .base_layers import BaseLayersManager
from .bng_plan_layers import BNGPlanLayersManager
from .geometry_handler import GeometryHandler
from .layer_factory import LayerFactory

__all__ = [
    'LayerManager', 
    'BaseLayersManager', 
    'BNGPlanLayersManager',
    'GeometryHandler',
    'LayerFactory'
]
