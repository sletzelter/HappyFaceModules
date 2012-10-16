import hf, logging
from sqlalchemy import *
from lxml import etree

def rare_to_GiB(rare_value):
    gib_value = rare_value/1024.0/1024.0/1024.0
    return round(gib_value,1)

def rare_to_TiB(rare_value):
    tib_value = rare_value/1024.0/1024.0/1024.0/1024.0
    return round(tib_value,1)

def rare_to_TB(rare_value):
    tb_value = rare_value/1000.0/1000.0/1000.0/1000.0
    return round(tb_value,1)


class dCacheDataManagement(hf.module.ModuleBase):
    config_keys = {
        'xml_source': ('URL of the XML file', '')
    }
    config_hint = ''
    last_chimera_timestamp=0
    last_details_id=0
    
    table_columns = [
        Column('chimera_timestamp', INT),   
        Column('latest_data_id', INT),
        Column('bare_total_files', INT),
        Column('bare_total_size', FLOAT),
        Column('bare_on_disk_files', INT),
        Column('bare_on_disk_size', FLOAT),
        Column('total_on_disk_files', INT),
        Column('total_on_disk_size', FLOAT),
    ], []

    subtable_columns = {'details': ([
        Column('name', TEXT),
        Column('bare_total_files', INT),
        Column('bare_total_size', FLOAT),
        Column('bare_on_disk_files', INT),
        Column('bare_on_disk_size', FLOAT),
        Column('total_on_disk_files', INT),
        Column('total_on_disk_size', FLOAT),
    ], []),}
    

    def prepareAcquisition(self):

        if 'xml_source' not in self.config: raise hf.exceptions.ConfigError('xml_source option not set')
        self.xml_source = hf.downloadService.addDownload(self.config['xml_source'])
        last_run= self.run['id']-1
        # needed inforamtion from last run
        if last_run>0:
            self.last_chimera_timestamp =  self.module_table.select(self.module_table.c.id== last_run).execute().fetchone().chimera_timestamp
            self.last_details_id = self.module_table.select(self.module_table.c.id== last_run).execute().fetchone().latest_data_id



        self.details_db_value_list = []

    def extractData(self):
        data = {'source_url': self.xml_source.getSourceUrl(),
                'chimera_timestamp':0,
                'latest_data_id':0,
                'bare_total_files':0,
                'bare_total_size':0.0,
                'bare_on_disk_files':0,
                'bare_on_disk_size':0.0,
                'total_on_disk_files':0,
                'total_on_disk_size':0.0,
                'status': 1.0}

        if self.xml_source.errorOccured() or not self.xml_source.isDownloaded():
            data['error_string'] = 'Source file was not downloaded. Reason: %s' % self.xml_source.error
            data['status'] = -1
            return data

        source_tree = etree.parse(open(self.xml_source.getTmpPath()))
        root = source_tree.getroot()


        cur_timestamp = int(root.find('time').text)
        data['chimera_timestamp'] = cur_timestamp
        is_new=0
        if cur_timestamp>self.last_chimera_timestamp:
            is_new=1
            data['latest_data_id']=self.run['id']
        else:
            data['latest_data_id']=self.last_details_id
	for element in root:
	    if element.tag == 'time':
                pass
	    elif element.tag == 'dataset':
                if is_new:
                    details_db_values = {}
                    details_db_values['name'] = element.attrib['name']
                    for subelement in element:
                        details_db_values[subelement.tag] =  int(subelement.text)
                    self.details_db_value_list.append(details_db_values)
	    else:
	        data[element.tag] = int(element.text)
        return data

    def fillSubtables(self, parent_id):
        self.subtables['details'].insert().execute([dict(parent_id=parent_id, **row) for row in self.details_db_value_list])

    def getTemplateData(self):
        data = hf.module.ModuleBase.getTemplateData(self)

        bare_total_files_rare = self.dataset['bare_total_files']
        bare_total_size_rare = self.dataset['bare_total_size']

        bare_on_disk_files_rare = self.dataset['bare_on_disk_files']
        bare_on_disk_size_rare = self.dataset['bare_on_disk_size']

        total_on_disk_size_rare = self.dataset['total_on_disk_size']

        self.dataset['bare_total_size_gib']=rare_to_GiB(bare_total_size_rare)
        self.dataset['bare_total_size_tib']=rare_to_TiB(bare_total_size_rare)
        self.dataset['bare_total_size_tb']=rare_to_TB(bare_total_size_rare)

     
        self.dataset['bare_on_disk_size_gib']=rare_to_GiB(bare_on_disk_size_rare)
        self.dataset['bare_on_disk_size_tib']=rare_to_TiB(bare_on_disk_size_rare)
        self.dataset['bare_on_disk_size_tb']=rare_to_TB(bare_on_disk_size_rare)

        if bare_total_size_rare>0:
            self.dataset['bare_on_disk_size_rel']=int(bare_on_disk_size_rare/bare_total_size_rare*100)
        else:
            self.dataset['bare_on_disk_size_rel']=0

        if bare_total_files_rare>0:
            self.dataset['bare_on_disk_files_rel']=int(bare_on_disk_files_rare/float(bare_total_files_rare)*100)
        else:
            self.dataset['bare_on_disk_files_rel']=0

        self.dataset['total_on_disk_size_gib']=rare_to_GiB(total_on_disk_size_rare )
        self.dataset['total_on_disk_size_tib']=rare_to_TiB(total_on_disk_size_rare )
        self.dataset['total_on_disk_size_tb']=rare_to_TB(total_on_disk_size_rare )

        info_list = self.subtables['details'].select().where(self.subtables['details'].c.parent_id==self.dataset['latest_data_id']).execute().fetchall() 
        info_list_expand =[]
        for info in info_list:
            name_rare = info.name
            bare_total_files_rare = info.bare_total_files
            bare_total_size_rare = info.bare_total_size
            bare_on_disk_files_rare = info.bare_on_disk_files
            bare_on_disk_size_rare =  info.bare_on_disk_size
            total_on_disk_files_rare =  info.total_on_disk_files
            total_on_disk_size_rare = info.total_on_disk_size

            info_expand= {}
            info_expand["name"] = name_rare
            info_expand["bare_total_files"]=bare_total_files_rare
            info_expand["bare_on_disk_files"]=bare_on_disk_files_rare
            if bare_total_files_rare > 0:
                info_expand["bare_on_disk_files_rel"]=int(bare_on_disk_files_rare/float(bare_total_files_rare)*100)
            else: 
                info_expand["bare_on_disk_files_rel"]=0
            info_expand["total_on_disk_files"]=total_on_disk_files_rare


            info_expand["bare_total_size"]=rare_to_GiB(bare_total_size_rare)
            info_expand["bare_on_disk_size"]=rare_to_GiB(bare_on_disk_size_rare)
            if bare_total_size_rare > 0:
                info_expand["bare_on_disk_size_rel"]=int(bare_on_disk_size_rare/bare_total_size_rare*100)
            else: 
                info_expand["bare_on_disk_size_rel"]=0
            info_expand["total_on_disk_size"]=rare_to_GiB(total_on_disk_size_rare)

            if info_expand["bare_on_disk_files_rel"] >=int(self.config['on_disk_th_files']):
                info_expand["bg_color"] = "#009966"
            else:
                info_expand["bg_color"] = "#FFFFFF"
            

            info_list_expand.append(info_expand)

        data['info_list'] = map(dict,info_list_expand)
        return data
