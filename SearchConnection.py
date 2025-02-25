def copyFunction(file_name, function_name):
    try:
        with open(file_name, 'r') as file:
            lines = file.readlines()

        function_found = False
        Open_Declaration_found = False
        function_lines = []
        function_lines_core = []
        for line in lines:
            # Check if we found the function definition
            if function_name in line and ";" not in line and "(" in line:
                function_found = True
                function_lines.append(line)

            if function_found and line.strip() == "{":
                Open_Declaration_found = True

            if function_found and Open_Declaration_found:
                function_lines.append(line)

            # Stop searching if we're past the function and not inside it
            if function_found and not Open_Declaration_found and line.strip() == "}":
                function_found = False
                function_lines.clear()

            # Stop searching if we're past the function and not inside it
            if function_found and Open_Declaration_found and line.strip() == "}":
                function_found = False
                Open_Declaration_found = False
                function_lines_core.extend(function_lines)
                function_lines.clear()

        return function_lines_core

    except FileNotFoundError:
        print(f"Error: File '{file_name}' not found.")
        return False


if __name__ == "__main__":
    file_name = "Software/Generated/src/rte/Rte.c"  # Change to your file name
    with open("Outputs/Log/didneaded", 'r') as file:
        content = file.read()
    names = content.split("\n")
    function_lines_core = []
    for function_name in names:
        function_lines_core.extend(copyFunction(file_name, function_name))
    with open("Outputs/Log/functionCore.c", 'w') as file:
        file.writelines(function_lines_core)
