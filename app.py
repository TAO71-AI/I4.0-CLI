# Import I4.0 utilities
from I4_0_Client.Utils import ServerUtilities
from I4_0_Client.Service import Service, ServiceManager

# TUI libraries
from colorama import Fore, Back

# Import other libraries
import os
import json
import time
import asyncio
import base64
import traceback

def Clear(PrintHelp: bool = False) -> None:
    if (os.name == "nt"):
        os.system("cls")
    else:
        os.system("clear")
    
    if (PrintHelp):
        print("Write ", end = "")
        PrintWithMode(2, "/help", End = "")
        print(" for help.")

def EditConfig() -> None:
    Clear()
    confirm = input("Are you sure you want to edit the current configuration? [y/N] ").lower().strip() == "y"

    if (not confirm):
        return
    
    config = ServerUtilities.Conf.__to_dict__()

    for param in list(config.keys()):
        Clear()
        print(f"Editing '{param}'.")
        print(f"Current value: {config[param]}")

        if (isinstance(config[param], list)):
            while (True):
                print("1. Add an item.")
                print("2. Delete an item.")

                action = input(f"'{param}' is a list. Select an action: ").strip()

                if (action == "1" or action == "1."):
                    item = input("Value: ")
                    config[param].append(item)
                elif (action == "2" or action == "2."):
                    if (len(config[param]) == 0):
                        print("No items.")
                        continue

                    for num, item in enumerate(config[param]):
                        print(f"{num + 1}. {item}")
                    
                    item = int(input("Item index: ")) - 1
                    config[param].remove(config[param][item])
                else:
                    break
        elif (isinstance(config[param], bool)):
            value = input(f"'{param}' is a boolean. New value (true or false): ").strip().lower()
            config[param] = value == "true" or value == "t" or value == "yes" or value == "y" or value == "1"
        elif (isinstance(config[param], int)):
            value = input(f"'{param}' is an integer. New value: ").strip()

            if (len(value) == 0):
                continue

            config[param] = int(value)
        elif (isinstance(config[param], float)):
            value = input(f"'{param}' is an integer. New value: ").strip()

            if (len(value) == 0):
                continue

            config[param] = float(value)
        elif (isinstance(config[param], str)):
            value = input(f"'{param}' is a text. New value (\"[e]\" for empty): ")
            
            if (len(value.strip()) == 0):
                continue

            if (value.lower().strip() == "[e]"):
                value = ""

            config[param] = value
        elif (config[param] is None):
            value = input(f"'{param}' is null. Will be converted to string. New value (\"[e]\" for empty): ")

            if (len(value.strip()) == 0):
                continue

            if (value.lower().strip() == "[e]"):
                value = ""

            config[param] = value
        else:
            print("Invalid value.")
            time.sleep(1)
    
    Clear()

    conf = json.dumps(config, indent = 4)
    confirm = input(f"{conf}\n\nIs this config OK? [Y/n] ").lower().strip() == "n"

    if (confirm):
        return
    
    ServerUtilities.Conf = ServerUtilities.Conf.__from_dict__(config)
    SaveConfig()

def SaveConfig() -> None:
    with open("config.json", "w+") as f:
        f.write(json.dumps(ServerUtilities.Conf.__to_dict__(), indent = 4))
    
    with open("extra_config.json", "w+") as f:
        f.write(json.dumps(extraConfig, indent = 4))
    
    ServerUtilities.__update_config__()

def PrintWithMode(Mode: int, Text: str, End: str = "\n", Flush: bool = False, Submode: int = 0) -> None:
    """
    Modes:
    - 0 = Normal
    - 1 = Thinking
    - 2 = Code
    - 3 = Error

    Submodes:
    - 0 = None
    - 1 = Bold
    - 2 = Italic
    - 3 = Bold + Italic
    """
    fore = ""
    smFore = ""
    back = ""

    if (Mode == 1):
        fore = extraConfig["think_mode_fg"]
        back = extraConfig["think_mode_bg"]
    elif (Mode == 2):
        fore = extraConfig["code_mode_fg"]
        back = extraConfig["code_mode_bg"]
    elif (Mode == 3):
        fore = extraConfig["error_fg"]
        back = extraConfig["error_bg"]
    else:
        fore = extraConfig["normal_fg"]
        back = extraConfig["normal_bg"]
    
    if (Submode == 1):
        smFore = "\033[1m"
    elif (Submode == 2):
        smFore = "\033[3m"
    elif (Submode == 3):
        smFore = "\033[1m\033[3m"
    else:
        smFore = "\033[0m"
    
    print(f"{smFore}{fore}{back}{Text}", end = extraConfig["normal_bg"] + extraConfig["normal_fg"] + End, flush = Flush)

async def SendPromptToServer(Serv: Service, Prompt: str, Files: list[dict[str, str]], Index: int) -> None:
    response = ServerUtilities.ExecuteService(
        Prompt,
        Files,
        Serv,
        Index,
        False,
        True
    )
    mode = 0
    subMode = 0
    nextMode = None
    nextSubMode = None
    lastToken = ""

    async for token in response:
        for tFile in token["files"]:
            if (tFile["type"] == "audio"):
                ext = "wav"
            elif (tFile["type"] == "image"):
                ext = "png"
            elif (tFile["type"] == "video"):
                ext = "mp4"
            else:
                PrintWithMode(3, "Unknown received file format. Extension will be 'unknown'.")
                ext = ".unknown"

            fID = 0
            tempName = f"temp_{fID}.{ext}"

            while (os.path.exists(tempName)):
                fID += 1
                tempName = f"temp_{fID}.{ext}"

            with open(tempName, "wb") as f:
                f.write(base64.b64decode(tFile["data"]))

        if (nextMode is None):
            if (token["response"].strip().startswith("```")):
                if (mode != 0):
                    nextMode = 0

                mode = 2
            elif (token["response"].strip().startswith("``")):
                mode = 2

                if (lastToken.strip().endswith("`")):
                    nextMode = 0
            elif (token["response"].strip().startswith("`") and lastToken.strip().endswith("``")):
                mode = 2
                nextMode = 0
            elif (token["response"].strip().startswith("<think>") and mode == 0):
                mode = 1
            elif (token["response"].strip().startswith("</think>") and mode == 1):
                mode = 1
                nextMode = 0
        else:
            mode = nextMode
            nextMode = None

        PrintWithMode(mode, token["response"], End = "", Flush = True, Submode = subMode)
        lastToken = token["response"]
    
    print("", flush = True)

async def ClearMemories() -> None:
    Clear()

    if (not ServerUtilities.ServerCon.IsConnected()):
        for idx, server in enumerate(ServerUtilities.Conf.Servers):
            print(f"Server #{idx + 1}: {server}")

        server = input(f"YOU'RE NOT CONNECTED TO ANY SERVER. PLEASE CONNECT TO ONE {inputChar} ")

        try:
            server = int(server) - 1
        except:
            pass

        await ServerUtilities.ServerCon.Connect(server)

    memMode = 1
    memResponse = ServerUtilities.ExecuteCommand("get_memories", "", -1)
    memStrRes = ""

    async for token in memResponse:
        memStrRes += str(token["response"])
    
    memStrRes = json.loads(memStrRes)

    if (len(memStrRes) == 0):
        PrintWithMode(2, "No memories.")
        return

    for idx, memText in enumerate(memStrRes):
        if (memMode == 1):
            memMode = 2
        else:
            memMode = 1

        PrintWithMode(memMode, f"Memory #{idx}: {memText}", Flush = True)
    
    print("")
    mem = input(f"MEMORY INDEX TO DELETE {inputChar} ")
                
    try:
        mem = int(mem)

        if (mem < 0 or mem >= len(memStrRes)):
            raise Exception()

        confirmMsg = f"YOU'RE ABOUT TO DELETE THE MEMORY #{mem}. ARE YOU SURE? [Y/n] "
    except:
        mem = -1
        confirmMsg = "YOU'RE ABOUT TO DELETE ALL THE MEMORIES. ARE YOU SURE? [Y/n] "

    confirm = input(confirmMsg).lower().strip() == "n"

    if (confirm):
        return
                
    await ServerUtilities.DeleteMemory(mem)
    Clear()

if (os.path.exists("config.json")):
    with open("config.json", "r") as f:
        ServerUtilities.Conf = ServerUtilities.Conf.__from_dict__(json.loads(f.read()))
    
    ServerUtilities.__update_config__()

if (os.path.exists("extra_config.json")):
    with open("extra_config.json", "r") as f:
        extraConfig = json.loads(f.read())
else:
    extraConfig = {
        "index": -1,
        "think_mode_bg": Back.RESET,
        "think_mode_fg": Fore.MAGENTA,
        "code_mode_bg": Back.BLACK,
        "code_mode_fg": Fore.YELLOW,
        "normal_bg": Back.RESET,
        "normal_fg": Fore.RESET,
        "error_bg": Back.RESET,
        "error_fg": Fore.RED,
        "service": Service.ToString(Service.Chatbot)
    }

loop = asyncio.new_event_loop()
lastErrorInfo = ""

Clear(True)

while (True):
    try:
        files = []
        prompt = ""
        inputChar = "$"

        while (True):
            tempPrompt = input(f"{inputChar} ")

            if (tempPrompt.lower().strip().endswith("/conf")):
                EditConfig()
                Clear(True)

                continue
            elif (tempPrompt.lower().strip().endswith("/bye")):
                Clear()
                SaveConfig()

                prompt = "/bye"
                break
            elif (tempPrompt.lower().strip().endswith("/bye!")):
                Clear()

                prompt = "/bye"
                break
            elif (tempPrompt.lower().strip().endswith("/idx")):
                Clear()

                index = input(f"INDEX {inputChar} ")
                extraConfig["index"] = int(index)

                Clear(True)
                continue
            elif (tempPrompt.lower().strip().endswith("/files")):
                Clear()

                while (True):
                    filePath = input(f"FILE #{len(files) + 1} PATH {inputChar} ").strip()

                    if (len(filePath) == 0):
                        break

                    if (not os.path.exists(filePath)):
                        print("FILE DOESN'T EXISTS")
                        continue

                    if (
                        filePath.lower().endswith(".png") or
                        filePath.lower().endswith(".jpg") or
                        filePath.lower().endswith(".jpeg")
                    ):
                        fileType = "image"
                    elif (
                        filePath.lower().endswith(".wav") or
                        filePath.lower().endswith(".mp3") or
                        filePath.lower().endswith(".flac")
                    ):
                        fileType = "audio"
                    elif (
                        filePath.lower().endswith(".avi") or
                        filePath.lower().endswith(".mp4") or
                        filePath.lower().endswith(".mkv")
                    ):
                        fileType = "video"
                    else:
                        print("UNKNOWN FILE TYPE. SPECIFY THE FILE TYPE")
                        fileType = input(f"(image, audio or video) {inputChar} ").lower().strip()

                        if (fileType != "image" and fileType != "audio" and fileType != "video"):
                            print("INVALID FILE TYPE. FILE NOT SAVED")
                            continue

                    files.append({"type": fileType, "data": filePath})
                
                Clear(True)
                continue
            elif (tempPrompt.lower().strip().endswith("/chserv") or tempPrompt.lower().strip().endswith("/chs")):
                extraConfig["service"] = ServiceManager.ToString(ServiceManager.FromString(input(f"SERVICE TO CHANGE {inputChar} ").lower().strip()))
                continue
            elif (tempPrompt.lower().strip().endswith("/clear") or tempPrompt.lower().strip().endswith("/cls")):
                Clear(True)
                continue
            elif (tempPrompt.lower().strip().endswith("/cc")):
                Clear()
                confirm = input("YOU'RE ABOUT TO DELETE THE CONVERSATION. ARE YOU SURE? [Y/n] ").lower().strip() == "n"

                if (confirm):
                    continue

                if (not ServerUtilities.ServerCon.IsConnected()):
                    for idx, server in enumerate(ServerUtilities.Conf.Servers):
                        print(f"Server #{idx + 1}: {server}")

                    server = input(f"YOU'RE NOT CONNECTED TO ANY SERVER. PLEASE CONNECT TO ONE {inputChar} ")

                    try:
                        server = int(server) - 1
                    except:
                        pass

                    loop.run_until_complete(ServerUtilities.ServerCon.Connect(server))

                loop.run_until_complete(ServerUtilities.DeleteConversation(None))
                Clear(True)

                continue
            elif (tempPrompt.lower().strip().endswith("/cm") or tempPrompt.lower().strip().endswith("/cms")):
                loop.run_until_complete(ClearMemories())
                continue
            elif (tempPrompt.lower().strip().endswith("/lasterr")):
                Clear(True)

                if (lastErrorInfo is None or len(lastErrorInfo.strip()) == 0):
                    print("No last error.")
                    continue

                print("Last error info:")
                PrintWithMode(3, lastErrorInfo)

                continue
            elif (tempPrompt.lower().strip().endswith("/help")):
                Clear()
                print("I4.0 CLI")
                print("\nAvailable commands:")

                PrintWithMode(2, "/conf", End = "")
                print(" - Edit the configuration.")

                PrintWithMode(2, "/bye", End = "")
                print(" - Close the program.")

                PrintWithMode(2, "/bye!", End = "")
                print(" - Close the program WITHOUT SAVING.")

                PrintWithMode(2, "/idx", End = "")
                print(" - Select an index.")

                PrintWithMode(2, "/files", End = "")
                print(" - Append files to the message.")

                PrintWithMode(2, "/clear", End = "")
                print(" or ", end = "")
                PrintWithMode(2, "/cls", End = "")
                print(" - Clear the screen.")

                PrintWithMode(2, "/cc", End = "")
                print(" - Clear or delete the conversation.")

                PrintWithMode(2, "/cm", End = "")
                print(" or ", end = "")
                PrintWithMode(2, "/cms", End = "")
                print(" - Delete a memory or memories.")

                PrintWithMode(2, "/lasterr", End = "")
                print(" - Print more information about the last error.")

                PrintWithMode(2, "/chserv", End = "")
                print(" or ", end = "")
                PrintWithMode(2, "/chs", End = "")
                print(f" - Change the service. [CURRENT SERVICE: {extraConfig['service']}]")

                PrintWithMode(2, "/end", End = "")
                print(" - Send the prompt to I4.0 and wait for an answer.")

                continue

            prompt += f"{tempPrompt}\n"
            
            if (tempPrompt.lower().strip().endswith("/end")):
                prompt = prompt[:prompt.lower().rfind("/end")].strip()

                break

            inputChar = ">"
        
        if (prompt.endswith("/bye")):
            break

        loop.run_until_complete(SendPromptToServer(ServiceManager.FromString(extraConfig["service"]), prompt, files, extraConfig["index"]))
    except KeyboardInterrupt:
        PrintWithMode(3, "\nTO CLOSE THE PROGRAM, PLEASE TYPE ", End = "")
        PrintWithMode(2, "/bye")
    except Exception as ex:
        PrintWithMode(3, "AN ERROR OCCURED. DETAILS: ", End = "")
        print(str(ex))
        PrintWithMode(3, "USE ", End = "")
        PrintWithMode(2, "/lasterr", End = "")
        PrintWithMode(3, " FOR MORE DETAILS.")

        lastErrorInfo = "\n".join(traceback.format_exception(ex))

loop.run_until_complete(ServerUtilities.ServerCon.Disconnect())
loop.close()
