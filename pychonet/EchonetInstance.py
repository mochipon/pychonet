# from ..eojx import *
from pychonet.lib.epc  import EPC_CODE, EPC_SUPER
from pychonet.lib.functions import buildEchonetMsg, sendMessage, decodeEchonetMsg, getOpCode
from pychonet.lib.epc_functions import EPC_FUNCTIONS, EPC_SUPER_FUNCTIONS

GETC = 			0x60
SETC = 			0x61
GET  = 			0x62
INFREQ =		0x63
SETGET = 		0x6E
SETRES =		0x71
GETRES =		0x72
INF =			0x73
INFC = 			0x74
INFC_RES =		0x7A
SETGET_RES =	0x7E
SETI_SNA = 		0x50
SETC_SND =		0x51
GET_SNA = 		0x52
INF_SNA = 		0x53
SETGET_SNA =	0x5E

ESV_CODES = {
	0x60: {'name': 'GetC', 'description': 'Property value write request (no response required)'},
	0x61: {'name': 'SetC', 'description': 'Property value write request (response required)'},
	0x62: {'name': 'Get', 'description': 'Property value read request'},
	0x63: {'name': 'INF_REQ', 'description': 'Property value notification request'},
	0x6E: {'name': 'SetGet', 'description': 'Property value write & read request'},
	0x71: {'name': 'Set_Res', 'description': 'Property value Property value write response'},
	0x72: {'name': 'Get_Res' , 'description': 'Property value read response'},
	0x73: {'name': 'INF' , 'description': 'Property value notification'},
	0x74: {'name': 'INFC', 'description': 'Property value notification (response required)'},
	0x7A: {'name': 'INFC_Res' , 'description': 'Property value notification response'},
	0x7E: {'name': 'SetGet_Res' , 'description': 'Property value write & read response'},
	0x50: {'name': 'SetI_SNA', 'description': 'Property value write request (response not possible)'},
	0x51: {'name': 'SetC_SNA' , 'description': 'Property value write request (response not possible)'},
	0x52: {'name': 'Get_SNA', 'description': 'Property value read (response not possible)'},
	0x53: {'name': 'INF_SNA', 'description': 'Property value notification (response not possible)'},
    0x5E: {'name': 'SetGet_SNA', 'description': 'Property value write & read (response not possible)'}
}

ENL_STATUS = 0x80
ENL_UID = 0x83
ENL_SETMAP = 0x9E
ENL_GETMAP = 0x9F

"""
Superclass for Echonet instance objects.
"""
class EchonetInstance:

    """
    Constructs an object to represent an Echonet lite instance .

    :param eojgc: Echonet group code
    :param eojcc: Echonet class code
    :param instance: Instance ID
    :param netif: IP address of node
    """
    def __init__(self, eojgc, eojcc, instance = 0x1, netif=""):
        self.netif = netif
        self.last_transaction_id = 0x01
        self.eojgc = eojgc
        self.eojcc = eojcc
        self.instance = instance
        self.available_functions = None
        self.status = False
        self.propertyMaps = self.getAllPropertyMaps()

    """
    getMessage is used to fire ECHONET request messages to get Node information
    Assumes one EPC is sent per message.

    :param tx_epc: EPC byte code for the request.
    :return: the deconstructed payload for the response

    """
    def getMessage(self, epc, pdc = 0x00):
        self.incrementTID()
        opc = [{'EPC': epc, 'PDC': pdc}]
        edt = getOpCode(self.netif, self.eojgc, self.eojcc, self.instance, opc, self.last_transaction_id )
        return edt


    """
    getSingleMessageResponse is used to fire ECHONET request messages to get Node information
    Assumes one EPC is sent per message. This is obsolete as 'update' can now peform the same function

    :param tx_epc: EPC byte code for the request.
    :return: the deconstructed payload for the response

    """
    def getSingleMessageResponse(self, epc):
         result = self.getMessage(epc)

         # safety check that we got a result for the correct code
         if len(result) > 0 and 'rx_epc' in result[0] and result[0]['rx_epc'] == epc:
             return result[0]['rx_edt']
         return None



    """
    setMessage is used to fire ECHONET request messages to set Node information
    Assumes one OPC is sent per message.

    :param tx_epc: EPC byte code for the request.
    :param tx_edt: EDT data relevant to the request.
    :return: True if sucessful, false if request message failed
    """
    def setMessage(self, opc):
        self.incrementTID()
        tx_payload = {
            'TID' : self.last_transaction_id,
            'DEOJGC': self.eojgc ,
            'DEOJCC': self.eojcc ,
            'DEOJIC': self.instance,
            'ESV' : SETC,
            'OPC' : opc
        }
        message = buildEchonetMsg(tx_payload)
        data = sendMessage(message, self.netif);
        ## some index issue here sometimes
        try:
           rx = decodeEchonetMsg(data[0]['payload'])
        # if no data is returned ignore the IndexError and return false
        except IndexError:
           return False
        return True

    """
    update is used as a way of producing a dict useful for API polling etc
    Data can be formatted or returned as a hex string value by default.

    :param attributes: optional list of EPC codes. eg [0x80, 0xBF], or a single code eg 0x80

    :return dict: A dict with the following attributes:
    {128: 'On', 160: 'medium-high', 176: 'heat', 129: '00', 130: '00004300',
    131: '0000060104a0c9a0fffe069719013001', 179: 19, 134: '06000006000000020000', 136: '42', 137: '0000'}

    :return string: if attribute is a single code then return value directly:
    eg:
    update(0x80)
    'on'

    """
    def update(self, attributes=None):
        # at this stage we only care about a subset of gettable attributes that are relevant
        # down the track i might try to pull all of them..
        opc = []
        if attributes == None:
            attributes = self.propertyMaps[ENL_GETMAP].values()
        if isinstance(attributes, int):
            list_attributes = [attributes]
            attributes = list_attributes
        returned_json_data = {}
        self.incrementTID()
        for value in attributes:
          if value in self.propertyMaps[ENL_GETMAP].values():
            opc.append({'EPC': value})
        raw_data = getOpCode(self.netif, self.eojgc, self.eojcc, self.instance, opc, self.last_transaction_id )
        if raw_data is not False:
             for data in raw_data:
                flag = 0
                if data['rx_epc'] in list(EPC_SUPER_FUNCTIONS.keys()): # check if function is defined in the superset
                    flag = 1
                    returned_json_data.update({data['rx_epc']: EPC_SUPER_FUNCTIONS[data['rx_epc']](data['rx_edt'])})
                elif data['rx_epc'] in list(EPC_SUPER.keys()): # return hex value if code exists in superset but no function found
                    flag = 1
                    returned_json_data.update({data['rx_epc']: data['rx_edt'].hex()})
                elif self.eojgc in list(EPC_FUNCTIONS.keys()):
                    if self.eojcc in list(EPC_FUNCTIONS[self.eojgc].keys()):
                        if data['rx_epc'] in list(EPC_FUNCTIONS[self.eojgc][self.eojcc].keys()): # check if function is defined for the specific class
                            flag = 1
                            returned_json_data.update({data['rx_epc']: EPC_FUNCTIONS[self.eojgc][self.eojcc][data['rx_epc']](data['rx_edt'])})
                if data['rx_epc'] in list(EPC_CODE[self.eojgc][self.eojcc].keys()) and flag == 0: # return hex value if EPC code exists in class but no function found
                        returned_json_data.update({data['rx_epc']: data['rx_edt'].hex()})
        for key in attributes:
            if key not in list(returned_json_data.keys()):
                returned_json_data.update({key: False})
        if(len(returned_json_data)) == 1 and len(attributes) == 1:
            return returned_json_data[attributes[0]]
        elif(len(returned_json_data)) == 0:
            return False
        return returned_json_data


    """
    getOperationalStatus returns the ON/OFF state of the node

    :return: status as a string.
    """
    def getOperationalStatus(self): # EPC 0x80
        return self.update(ENL_STATUS)

    """
    setOperationalStatus sets the ON/OFF state of the node

    :param status: True if On, False if Off.
    """
    def setOperationalStatus(self, status): # EPC 0x80
        return self.setMessage([{'EPC': ENL_STATUS, 'PDC': 0x01, 'EDT': 0x30 if status else 0x31}])

    """
    On sets the node to ON.

    """
    def on (self): # EPC 0x80
        return self.setMessage([{'EPC': ENL_STATUS, 'PDC': 0x01, 'EDT': 0x30}])

    """
    Off sets the node to OFF.

    """
    def off (self): # EPC 0x80
        return self.setMessage([{'EPC': ENL_STATUS, 'PDC': 0x01, 'EDT': 0x31}])

    def fetchSetProperties (self): # EPC 0x9E
        if 0x9E in self.propertyMaps:
            return self.propertyMaps[ENL_SETMAP]
        else:
            return {}

    def fetchGetProperties (self): # EPC 0x9F
        if 0x9F in self.propertyMaps:
            return self.propertyMaps[ENL_GETMAP]
        else:
            return {}

    def incrementTID (self):
        self.last_transaction_id += 0x01
        if self.last_transaction_id > 0xFFFF:
            self.last_transaction_id = 0x01
    """
    getIdentificationNumber returns a number used to identify an object uniquely

    :return: Identification number as a string.
    """
    def getIdentificationNumber(self): # EPC 0x83
        return self.update(ENL_UID)

    def getAllPropertyMaps(self):
        propertyMaps = {}
        property_map = getOpCode(self.netif, self.eojgc, self.eojcc, self.instance, [{'EPC':ENL_GETMAP},{'EPC':ENL_SETMAP}])
        for property in property_map:
            propertyMaps[property['rx_epc']] = {}
            for value in EPC_SUPER_FUNCTIONS[0x9F](property['rx_edt']):
                if value in EPC_CODE[self.eojgc][self.eojcc]:
                    propertyMaps[property['rx_epc']][EPC_CODE[self.eojgc][self.eojcc][value]] = value
                elif value in EPC_SUPER:
                    propertyMaps[property['rx_epc']][EPC_SUPER[value]] = value
        return propertyMaps
