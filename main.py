import sys
import translator

def main():
    if len(sys.argv) == 1:
        print("Usage: python3 %s input_file1 input_file2 ..." % sys.argv[0])
    file_list = sys.argv[1:]
    t = translator.Translator()
    for it in file_list:
        t.append(it)
    
    t.translate(sys.stdout)


if __name__ == "__main__":
    main()