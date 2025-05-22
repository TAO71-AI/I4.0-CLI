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
    await AskConnectToServer()
    response = ServerUtilities.ExecuteService(
        Prompt,
        Files,
        Serv,
        Index,
        True,
        True
    )
    mode = 0
    subMode = 0
    nextMode = None
    nextSubMode = None
    lastToken = ""
    thinkTime = None

    async for token in response:
        for error in token["errors"]:
            PrintWithMode(3, f"Error in the server: {error}")

        for tFile in token["files"]:
            if (tFile["type"] == "audio"):
                ext = "wav"
            elif (tFile["type"] == "image"):
                ext = "png"
            elif (tFile["type"] == "video"):
                ext = "mp4"
            elif (tFile["type"] == "pdf"):
                ext = "pdf"
            elif (tFile["type"] == "docx"):
                ext = "docx"
            else:
                PrintWithMode(3, f"Unknown received file format. Extension will be '{tFile['type']}'.")
                ext = tFile["type"]

            fID = 0
            tempName = f"temp_{fID}.{ext}"

            while (os.path.exists(tempName)):
                fID += 1
                tempName = f"temp_{fID}.{ext}"

            with open(tempName, "wb") as f:
                f.write(base64.b64decode(tFile["data"]))

        if (nextMode is None):
            if (
                token["response"].strip().startswith("```") or
                (token["response"].strip().startswith("``") and lastToken.endswith("`")) or
                (token["response"].strip().startswith("`") and lastToken.strip().endswith("``"))
            ):
                if (mode != 0):
                    nextMode = 0

                mode = 2
            elif (token["response"].strip().startswith("<think>") and mode == 0):
                mode = 1

                if (not extraConfig["show_think"]):
                    PrintWithMode(mode, "<thinking...>", Flush = True, Submode = subMode)
                    thinkTime = time.time()
            elif (token["response"].strip().startswith("</think>") and mode == 1):
                mode = 1
                nextMode = 0

                if (not extraConfig["show_think"]):
                    thinkTime = time.time() - thinkTime
                    thinkTime = round(thinkTime, 1)

                    PrintWithMode(mode, f"<thought for {thinkTime} seconds>", Flush = True, Submode = subMode)
                    thinkTime = None
        else:
            mode = nextMode
            nextMode = None

        if (mode == 1 and not extraConfig["show_think"]):
            continue

        PrintWithMode(mode, token["response"], End = "", Flush = True, Submode = subMode)
        lastToken = token["response"]
    
    print("", flush = True)

async def ClearMemories() -> None:
    Clear()
    await AskConnectToServer()

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
    mem = input("MEMORY INDEX TO DELETE # ")
                
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
    Clear(True)

async def DownloadAndPrintConversation() -> None:
    Clear(True)

    await AskConnectToServer()
    response = ServerUtilities.ExecuteCommand("get_conversation", "", -1)
    fullJson = ""

    async for res in response:
        fullJson += res["response"]

    fullJson = json.loads(fullJson)

    if (len(fullJson) > 0):
        print(" [ ## CONVERSATION RESTORED ## ] ")

    for message in fullJson:
        messageFiles = 0

        for cont in message["content"]:
            if (cont["type"] != "text"):
                messageFiles += 1
                continue

            if (message["role"] == "user"):
                for line in cont["text"].split("\n"):
                    print(f"$ {cont['text']}", flush = True)
            else:
                mode = 0
                subMode = 0

                for line in cont["text"].split("\n"):
                    if (line.count("```") > 0):
                        if (mode == 0):
                            print(line[:line.index("```")], end = "", flush = True)
                            PrintWithMode(2, line[line.index("```"):], Flush = True)

                            mode = 2
                            continue
                        elif (mode == 2):
                            PrintWithMode(2, line[:line.index("```") + 3], End = "", Flush = True)
                            print(line[line.index("```") + 3:], flush = True)

                            mode = 0
                            continue
                    elif (line.count("<think>") > 0):
                        print(line[:line.index("<think>")], end = "", flush = True)
                        PrintWithMode(1, line[line.index("<think>"):], Flush = True)

                        mode = 1
                        continue
                    elif (line.count("</think>") > 0):
                        PrintWithMode(1, line[:line.index("</think>") + 8], End = "", Flush = True)
                        print(line[line.index("</think>") + 8:], flush = True)

                        mode = 0
                        continue

                    PrintWithMode(mode, line, Flush = True)

async def AskConnectToServer() -> None:
    if (ServerUtilities.ServerCon.IsConnected()):
        return

    await ServerUtilities.ServerCon.Connect(0)

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
        "code_mode_bg": Back.RESET,
        "code_mode_fg": Fore.YELLOW,
        "normal_bg": Back.RESET,
        "normal_fg": Fore.RESET,
        "error_bg": Back.RESET,
        "error_fg": Fore.RED,
        "service": ServiceManager.ToString(Service.Chatbot),
        "show_think": False
    }

loop = asyncio.new_event_loop()
lastErrorInfo = ""

Clear(True)
loop.run_until_complete(DownloadAndPrintConversation())

while (True):
    try:
        files = []
        prompt = ""

        while (True):
            tempPrompt = input("$ ")

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

                index = input("INDEX # ")
                extraConfig["index"] = int(index)

                Clear(True)
                continue
            elif (tempPrompt.lower().strip().endswith("/files")):
                Clear()

                while (True):
                    filePath = input(f"FILE #{len(files) + 1} PATH $ ").strip()

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
                        fileType = input("(image, audio or video) $ ").lower().strip()

                        if (fileType != "image" and fileType != "audio" and fileType != "video"):
                            print("INVALID FILE TYPE. FILE NOT SAVED")
                            continue

                    files.append({"type": fileType, "data": filePath})
                
                Clear(True)
                continue
            elif (tempPrompt.lower().strip().endswith("/chserv") or tempPrompt.lower().strip().endswith("/chs")):
                extraConfig["service"] = ServiceManager.ToString(ServiceManager.FromString(input("SERVICE TO CHANGE $ ").lower().strip()))
                continue
            elif (tempPrompt.lower().strip().endswith("/clear") or tempPrompt.lower().strip().endswith("/cls")):
                Clear(True)
                continue
            elif (tempPrompt.lower().strip().endswith("/cc")):
                Clear()
                confirm = input("YOU'RE ABOUT TO DELETE THE CONVERSATION. ARE YOU SURE? [Y/n] ").lower().strip() == "n"

                if (confirm):
                    continue

                loop.run_until_complete(AskConnectToServer())
                loop.run_until_complete(ServerUtilities.DeleteConversation(None))

                Clear(True)
                continue
            elif (tempPrompt.lower().strip().endswith("/cm") or tempPrompt.lower().strip().endswith("/cms")):
                loop.run_until_complete(ClearMemories())
                continue
            elif (tempPrompt.lower().strip().endswith("/tg_think")):
                extraConfig["show_think"] = not extraConfig["show_think"]
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
                print(f" - Select an index. [CURRENT: {extraConfig['index']}]")

                PrintWithMode(2, "/files", End = "")
                print(f" - Append files to the message. [{len(files)} FILES ATTACHED]")

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

                PrintWithMode(2, "/tg_think", End = "")
                print(f" - Toggle thinking. [CURRENT: {extraConfig['show_think']}]")

                PrintWithMode(2, "/end", End = "")
                print(" - Send the prompt to I4.0 and wait for an answer.")

                continue
            elif (len(tempPrompt.strip()) == 0):
                continue

            prompt += f"{tempPrompt}\n"
            
            if (tempPrompt.lower().strip().endswith("/end")):
                prompt = prompt[:prompt.lower().rfind("/end")].strip()

                break
        
        if (prompt.endswith("/bye")):
            break

        loop.run_until_complete(SendPromptToServer(ServiceManager.FromString(extraConfig["service"]), prompt, files, extraConfig["index"]))
        loop.run_until_complete(ServerUtilities.ServerCon.Disconnect())
    except KeyboardInterrupt:
        try:
            loop.run_until_complete(ServerUtilities.ServerCon.Disconnect())
        except:
            pass

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

loop.run_until_complete(ServerUtilities.ServerCon.Disconnect())
loop.close()
