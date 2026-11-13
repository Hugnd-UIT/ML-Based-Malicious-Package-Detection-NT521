# Sensitivity: d120-fake vs d60-fake vs d300-fake (model Random-Forest)

Reference run: `d120-fake`. 'Changed' = numeric feature moving more than 20%.

| Package | Label | d120-fake pred (prob) | d60-fake pred (prob) | d300-fake pred (prob) | Flip | Changed features |
|---|---|---|---|---|---|---|
| benign-config | 0 | ben (0.50) | ben (0.50) | MAL (0.73) | **YES** | Local_Port_Access 17->46 |
| benign-netcheck | 0 | MAL (0.54) | ben (0.37) | MAL (0.50) | **YES** | Temporary_DIR_Installation 943->1407; Local_IP_Address_Access 2->1; Remote_IP_Address_Access 3->2; Local_Port_Access 120->3; Remote_Port_Access 4->3; File_Operations 2074->2604 ... |
| flask | 0 | MAL (0.85) | MAL (0.85) | ben (0.46) | **YES** | Local_IP_Address_Access 1->0; Remote_IP_Address_Access 1->0; Local_Port_Access 34->0; Remote_Port_Access 1->0; File_Operations 0->10785; Network_Operations 0->2 ... |
| requests | 0 | MAL (0.85) | MAL (0.82) | MAL (0.63) |  | Local_IP_Address_Access 1->0; Remote_IP_Address_Access 1->0; Local_Port_Access 90->0; Remote_Port_Access 1->0; File_Operations 0->5704; Process_Management_Operations 0->26 ... |
| sim-delayed | 1 | MAL (0.54) | MAL (0.64) | MAL (0.71) |  | Temporary_DIR_Installation 1448->35; User_Access 1854->1344; Local_IP_Address_Access 0->1; Remote_IP_Address_Access 0->1; Local_Port_Access 0->60; Remote_Port_Access 0->1 ... |
| sim-dropper | 1 | MAL (0.62) | MAL (0.62) | ben (0.49) | **YES** | Temporary_DIR_Installation 248->1389; User_Access 1344->1864; Local_Port_Access 73->156; File_Operations 2910->1490; Process_Management_Operations 57->42; IO_Operations 235->129 |
| sim-exfil-file | 1 | MAL (0.78) | ben (0.41) | ben (0.44) | **YES** | Temporary_DIR_Installation 836->1258; Local_IP_Address_Access 2->1; Remote_IP_Address_Access 3->2; Local_Port_Access 60->3; Remote_Port_Access 4->3; File_Operations 3468->1666 ... |
| six | 0 | ben (0.39) | MAL (0.83) | MAL (0.83) | **YES** | Local_IP_Address_Access 1->0; Remote_IP_Address_Access 1->0; Local_Port_Access 77->0; Remote_Port_Access 1->0; File_Operations 5160->0; Network_Operations 2->0 ... |

6/8 packages change verdict between runs.
