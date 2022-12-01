import yaml
class Triggers():
    dict_legtypes = {"Electron":"Leg::e", "Muon":"Leg::mu", "Tau":"Leg::tau"}

    def __init__(self, triggerFile):
        with open(triggerFile, "r") as stream:
            self.trigger_dict= yaml.safe_load(stream)
        self.deltaR_matching = 0.4


    def ApplyTriggers(self, df, isData = False):
        hltBranches = []
        df = df.Define(f"TrigObj_idx", f"CreateIndexes(TrigObj_pt.size())").Define("TrigObj_mass", "RVecF mass ; for(int i =0; i< TrigObj_pt.size(); i++){mass.push_back(0.);} return mass;")
        df = df.Define(f"TrigObj_p4", f"GetP4(TrigObj_pt,TrigObj_eta,TrigObj_phi, TrigObj_mass, TrigObj_idx)")
        for path, path_dict in self.trigger_dict.items():
            path_key = 'path'
            if 'path' not in path_dict:
                path_key += '_data' if isData else '_MC'
            or_paths = " || ".join(path for path in path_dict[path_key])
            or_paths = f' ( { or_paths } ) '
            additional_conditions = [""]
            total_objects_matched = []
            for leg_id, leg_tuple in enumerate(path_dict['legs']):
                leg_dict_offline= leg_tuple["offline_obj"]
                type_name_offline = leg_dict_offline["type"]
                var_name_offline = f'{type_name_offline}_offlineCut_{leg_id+1}_{path}'
                df = df.Define(var_name_offline, leg_dict_offline["cut"])
                if not leg_tuple["doMatching"]:
                    if(leg_dict_offline["type"]!='MET'):
                        var_name_offline = f'{leg_dict_offline["type"]}_idx[{var_name_offline}].size()>0'
                    additional_conditions.append(f' {var_name_offline} ')
                else:
                    df = df.Define(f'{type_name_offline}_{var_name_offline}_sel', f'httCand.isLeg({type_name_offline}_idx, {self.dict_legtypes[type_name_offline]}) && ({var_name_offline})')
                    leg_dict_online= leg_tuple["online_obj"]
                    var_name_online =  f'{leg_dict_offline["type"]}_onlineCut_{leg_id+1}_{path}'
                    df = df.Define(f'{var_name_online}',f'{leg_dict_online["cut"]}')
                    matching_var = f'{leg_dict_offline["type"]}_Matching_{leg_id+1}_{path}'
                    df = df.Define(f'{matching_var}', f"""FindMatchingSet({var_name_online}, {type_name_offline}_{var_name_offline}_sel,
                                                                            TrigObj_p4, {leg_dict_offline["type"]}_p4, {self.deltaR_matching} )""")
                    total_objects_matched.append(f'{{ {self.dict_legtypes[type_name_offline]}, {matching_var} }}')

            legVector = f'{{ { ", ".join(total_objects_matched)} }}'
            df = df.Define(f'hasHttCandCorrespondance_{path}', f'HasOOMatching({legVector} )')
            stringToAppend = f'{or_paths} &&  hasHttCandCorrespondance_{path}'
            stringToAppend += ' && '.join(additional_conditions)
            hltBranch = f'HLT_{path}'
            hltBranches.append(hltBranch)
            df = df.Define(hltBranch, stringToAppend)
        total_or_string = ' || '.join(hltBranches)
        df = df.Filter(total_or_string)
        return df,hltBranches
