# BNGAI QGIS Plugin – Do / Don’t Guide

This short note captures day-to-day etiquette for working with the BNGAI layers inside QGIS. It reflects the behaviour of the current release and should help avoid the most common sync surprises.

## Do

- When performing bulk edits against habitat layers, always use the code value from the table below. These lowercase code strings are what the API expects, so sticking to them prevents validation errors later on.

| Label                                    | Code value                        |
| ---------------------------------------- | --------------------------------- |
| Good                                     | `good`                            |
| Fairly Good                              | `fairly good`                     |
| Moderate                                 | `moderate`                        |
| Fairly Poor                              | `fairly poor`                     |
| Poor                                     | `poor`                            |
| N/A - Other                              | `NA - other`                      |
| Condition Assessment N/A                 | `condition assessment NA`         |
| Low (strategic significance)             | `low`                             |
| Medium (strategic significance)          | `medium`                          |
| High (strategic significance)            | `high`                            |
| Very Low (distinctiveness)               | `very_low`                        |
| Low (distinctiveness)                    | `low`                             |
| Medium (distinctiveness)                 | `medium`                          |
| High (distinctiveness)                   | `high`                            |
| Very High (distinctiveness)              | `very_high`                       |
| Watercourse Major                        | `major`                           |
| Watercourse Minor                        | `minor`                           |
| Watercourse No Encroachment              | `no_encroachment`                 |
| Riparian Major/Major                     | `major-major`                     |
| Riparian Major/Moderate                  | `major-moderate`                  |
| Riparian Major/Minor                     | `major-minor`                     |
| Riparian Major/No Encroachment           | `major-no_encroachment`           |
| Riparian Moderate/Moderate               | `moderate-moderate`               |
| Riparian Moderate/Minor                  | `moderate-minor`                  |
| Riparian Moderate/No Encroachment        | `moderate-no_encroachment`        |
| Riparian Minor/Minor                     | `minor-minor`                     |
| Riparian Minor/No Encroachment           | `minor-no_encroachment`           |
| Riparian No Encroachment/No Encroachment | `no_encroachment-no_encroachment` |
| Tree size small                          | `small`                           |
| Tree size medium                         | `medium`                          |
| Tree size large                          | `large`                           |
| Tree size very large                     | `very_large`                      |

## Don’t / Avoid

- After running a sync, delete both the **Plan** and **Retained Habitats** layers and reload them. This ensures the map reflects the newly updated server state rather than cached geometries.
- Commit/save any layer edits before you press the sync button. Uncommitted edits are ignored by the synchroniser and are lost once the layer reloads.
- Only work on **one plan at a time** inside QGIS. Having two plans open while syncing can mix feature IDs and cause conflicts on upload.
- Avoid editing the same plan simultaneously across QGIS, the web dashboard, and the mobile app. Concurrent edits across platforms are not merged and will almost certainly lead to overwrite conflicts.
- On plan layers, avoid creating overlapping polygons. If you need holes, create rings and fill them rather than stacking polygons on top of one another.

Following these habits should keep your workflow tidy and prevent most sync issues. If anything unexpected still happens, capture the steps you took and share them with the BNGAI team so we can investigate.
