# Sensitivity: w2 vs w3 (model Random-Forest)

Reference run: `w2`. 'Changed' = numeric feature moving more than 20%.

| Package | Label | w2 pred (prob) | w3 pred (prob) | Flip | Changed features |
|---|---|---|---|---|---|
| 1337x | 0 | MAL (0.61) | ben (0.32) | **YES** | Temporary_DIR_Installation 288->127; Home_DIR_Installation 1265->376; User_Access 4906->820; Sys_Access 1261->106; Etc_DIR_Installation 1110->131; Other_DIR_Installation 523437->39610 ... |
| Acquisition | 0 | ben (0.38) | ben (0.07) |  | User_Access 4830->836; Sys_Access 1240->126; Etc_DIR_Installation 1496->122; Other_DIR_Installation 516823->40033; Remote_IP_Address_Access 3->4; Local_Port_Access 4->6 ... |
| adafruit-io | 0 | ben (0.20) | ben (0.08) |  | Root_DIR_Installation 32->0; Temporary_DIR_Installation 2736->82; Home_DIR_Installation 1756->676; User_Access 8393->1047; Sys_Access 1320->98; Etc_DIR_Installation 1349->126 ... |
| flask | 0 | MAL (0.72) | ben (0.38) | **YES** | User_Access 4898->836; Sys_Access 1319->96; Etc_DIR_Installation 1119->118; Other_DIR_Installation 529114->39900 |
| requests | 0 | MAL (0.69) | MAL (0.66) |  | User_Access 4902->836; Sys_Access 1331->99; Etc_DIR_Installation 1189->121; Other_DIR_Installation 528771->39161; Remote_IP_Address_Access 3->2; File_Operations 6899->5348 ... |

2/5 packages change verdict between runs.
