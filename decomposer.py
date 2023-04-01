import json
import os

tmp_list = {}
categories = ['bipods', 'foregrips', 'flashlights', 'tactical_combo_devices', 'auxiliary_parts', 
'muzzle_adapters', 'flash_hiders_muzzle_brakes', 'suppressors', 
'assault_scopes', 'reflex_sights', 'compact_reflex_sights', 'iron_sights', 'scopes', 'special_scopes', 
'charging_handles', 'magazines', 'mounts', 'stocks_chassis', 
'barrels', 'gas_blocks', 'handguards', 'pistol_grips', 'receivers_slides']

def _decompose():
    if os.path.exists('./json/src'):
        pass
    else:
        os.makedirs('./json/src')

    with open("./json/mods.json", "r") as mods_dictionary_file:
        tmp = json.load(mods_dictionary_file)

        category_idx = 0
        idx = 0
        for i in tmp:
            for tabber in tmp[idx]:
                tmp_list = tabber.copy()
                outfile = open('./json/src/{}.json'.format(categories[category_idx]), 'w')
                json.dump(tmp_list, outfile, indent=4)
                outfile.close()
                category_idx += 1
            idx += 1
        
if __name__ == "__main__":
    _decompose()