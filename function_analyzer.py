import idaapi
import ida_name
import ida_kernwin
import ida_funcs
import requests
import json
import threading
import ida_typeinf


HOTKEY = "Ctrl-Shift-X"


def process_server_response(response_text, status_code):
    print(f"Server Status: {status_code}")
    
    try:
        response_data = json.loads(response_text)
    except Exception as e:
        print(f"Error processing server response: {e}")
        return
    
    # Fixed: Check for success field properly and handle both True/False cases
    if 'success' not in response_data:
        print("Missing 'success' field in response")
        return
        
    if not response_data['success']:
        # Fixed: Handle error field properly when success is False
        error_msg = response_data.get('error', 'Unknown error')
        print(f"Server reported failure: {error_msg}")
        return
    
    # Fixed: Only proceed if success is True
    if 'data' not in response_data:
        print("Missing 'data' field in successful response")
        return
    
    data = response_data['data']
    
    # Fixed: Add validation for required fields in data
    if not isinstance(data, dict):
        print("'data' field is not an object")
        return
        
    if 'analyzed_function_address' not in data:
        print("Missing 'analyzed_function_address' in data")
        return
        
    if 'suggested_function_name' not in data:
        print("Missing 'suggested_function_name' in data")
        return
    
    try:
        address = int(data['analyzed_function_address'], 16)
    except (ValueError, TypeError) as e:
        print(f"Invalid function address format: {e}")
        return
        
    function_name = data['suggested_function_name']
    
    if not function_name or not isinstance(function_name, str):
        print("Invalid function name")
        return
    
    print(f"Setting name for function at 0x{address:X} to '{function_name}'")
    ida_name.set_name(address, function_name, ida_name.SN_CHECK)

    process_parameters(data, address)
    process_called_functions(data)


def process_parameters(data, address):
    if 'parameters' not in data or not isinstance(data['parameters'], list):
        return
    
    func_tinfo = ida_typeinf.tinfo_t()
    
    success = False
    try:
        success = ida_typeinf.get_tinfo(func_tinfo, address)
    except AttributeError:
        try:
            success = func_tinfo.get_type_by_ea(address)
        except AttributeError:
            print(f"Warning: Cannot get type info for function at 0x{address:X}")
            return
    
    if not success:
        return
    
    funcdata = ida_typeinf.func_type_data_t()
    if not func_tinfo.get_func_details(funcdata):
        return
    
    changed_params = False
    
    for param_info in data['parameters']:
        if update_parameter(param_info, funcdata, address):
            changed_params = True
    
    if changed_params:
        new_func_tinfo = ida_typeinf.tinfo_t()
        new_func_tinfo.create_func(funcdata)
        ida_typeinf.apply_tinfo_to_ea(address, new_func_tinfo, ida_typeinf.NTF_REPLACE)


def update_parameter(param_info, funcdata, address):
    original_name = param_info.get('original_name')
    suggested_name = param_info.get('suggested_name')
    
    if not suggested_name:
        return False
    
    param_idx = get_parameter_index(original_name)
    
    if param_idx < 0 or param_idx >= funcdata.size():
        print(f"  Warning: Parameter '{original_name}' (parsed idx {param_idx}) could not be mapped or is out of bounds for function 0x{address:X} (num args: {funcdata.size()}).")
        return False
    
    if funcdata[param_idx].name == suggested_name:
        return False
    
    print(f"  Setting param '{funcdata[param_idx].name}' (idx {param_idx}, orig: {original_name}) to '{suggested_name}' for func 0x{address:X}")
    funcdata[param_idx].name = suggested_name
    return True


def get_parameter_index(original_name):
    if not original_name or not isinstance(original_name, str):
        return -1
    
    if not original_name.startswith('a') or not original_name[1:].isdigit():
        return -1
    
    try:
        return int(original_name[1:]) - 1
    except ValueError:
        return -1


def process_called_functions(data):
    if 'called_functions' not in data or not isinstance(data['called_functions'], list):
        return
    
    for called_func_info in data['called_functions']:
        process_single_called_function(called_func_info)


def process_single_called_function(called_func_info):
    if not isinstance(called_func_info, dict):
        return
    
    if 'address' not in called_func_info or 'suggested_name' not in called_func_info:
        return
    
    called_func_addr_str = called_func_info['address']
    called_func_name = called_func_info['suggested_name']
    
    if not called_func_name:
        return
    
    try:
        called_func_ea = int(str(called_func_addr_str), 0)
    except ValueError:
        print(f"Error: Invalid address format for called function: '{called_func_addr_str}'.")
        return
    
    if called_func_ea != idaapi.BADADDR:
        print(f"Setting name for called function at 0x{called_func_ea:X} to '{called_func_name}'")
        ida_name.set_name(called_func_ea, called_func_name, ida_name.SN_CHECK)
    else:
        print(f"Warning: BADADDR (0x{idaapi.BADADDR:X}) received for called function name '{called_func_name}'.")


def make_network_request(code_str):
    try:
        r = requests.post(
            'http://127.0.0.1:13337/analyze',
            data=code_str.encode('utf-8'),
            headers={'Content-Type': 'text/plain'},
            timeout=60
        )

        r.raise_for_status()

        ida_kernwin.execute_sync(
            lambda: process_server_response(r.text, r.status_code),
            ida_kernwin.MFF_WRITE
        )
        
    except Exception as e:
        ida_kernwin.execute_sync(lambda: ida_kernwin.warning(f"An unexpected error occurred in the network thread: {e}"), ida_kernwin.MFF_NOWAIT)


def send_request():
    ea = ida_kernwin.get_screen_ea()
    if ea == idaapi.BADADDR:
        return

    func = ida_funcs.get_func(ea)
    if not func:
        return

    try:
        cfunc = idaapi.decompile(func)
    except idaapi.DecompilationFailure as e:
        ida_kernwin.warning(f"Decompilation failed: {e}")
        return

    if not cfunc:
        ida_kernwin.warning("Failed to decompile function (decompiler returned None).")
        return

    pseudocode_lines = cfunc.get_pseudocode()
    lines = [idaapi.tag_remove(line.line) for line in pseudocode_lines]
    code_str = "\n".join(lines)

    if not code_str.strip():
        ida_kernwin.warning("Decompiled code is empty.")
        return

    thread = threading.Thread(target=make_network_request, args=(code_str,))
    thread.daemon = True
    thread.start()


def unbind_and_bind_hotkey():

    if ida_kernwin.del_hotkey(HOTKEY):
        print(f"Existing binds unbound from '{HOTKEY}'.")

    if ida_kernwin.add_hotkey(HOTKEY, send_request):
        print(f"Binded to '{HOTKEY}'.")


unbind_and_bind_hotkey()