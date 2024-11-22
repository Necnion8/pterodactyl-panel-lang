import sys
import json
from pathlib import Path


def parse_string(s):
    s = s.strip()
    if s.endswith(","):
        s = s[:-1]
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1].replace("\\'", "'")
    elif s.startswith('"') and s.endswith('"'):
        return s[1:-1].replace('\\"', '"')
    raise ValueError(f"Bracket invalid: {s!r}")


def load_from(src: Path):
    _lang = {}
    with open(src, "r", encoding="utf8") as f:
        _keys = []
        for line in f:
            line = line.strip()

            # nest out
            if line.startswith("]"):
                if line.endswith(";"):  # file ends
                    continue
                _keys.pop(-1)

            # other line
            elif not line.startswith("'") and not line.startswith('"'):
                continue

            # nest in
            elif line.endswith("["):
                key = line[1:line.rindex(line[0])]
                _keys.append(key)

            # value
            elif line.count("=>"):
                sp = line.index("=>")
                #
                key = parse_string(line[:sp])
                try:
                    value = parse_string(line[sp+2:])
                except ValueError as e:
                    print("WARN: ignored:", src, f"{key!r}", e)
                    continue

                _key = ".".join([*_keys, key])
                _lang[_key] = value

            # value list
            elif line.endswith("'") or line.endswith("',") or line.endswith('"') or line.endswith('",'):
                _key = ".".join(_keys)
                _lang.setdefault(_key, []).append(parse_string(line))

            else:
                raise ValueError(f"WARN: Unhandled line: {line!r}")
    return _lang


def load_to_remap_dump(src: Path, lang: dict):
    with open(src, "r", encoding="utf8") as f:
        _lines = []
        _keys = []

        for _line in f:
            line = _line.strip()
            offset_left = _line.index(line)
            offset_right = _line.rindex(line)
            _line = _line.rstrip()

            # nest out
            if line.startswith("]"):
                if not line.endswith(";"):  # file ends
                    _keys.pop(-1)

            # other line
            elif not line.startswith("'") and not line.startswith('"'):
                pass

            # nest in
            elif line.endswith("["):
                key = line[1:line.rindex(line[0])]
                _keys.append(key)

                _key = ".".join(_keys)
                if _key in lang:
                    new_value = lang[_key]
                    if isinstance(new_value, list):
                        _lines.append(_line)
                        for val in new_value:
                            __line = " " * (offset_left + 4) + "'" + val.replace("'", "\\'") + "',"
                            _lines.append(__line)
                        continue

            # value
            elif line.count("=>"):
                sp = line.index("=>")
                #
                key = parse_string(line[:sp])
                try:
                    value = parse_string(line[sp+2:])
                except ValueError as e:
                    print("WARN: ignored:", src, f"{key!r}", e)

                else:
                    _key = ".".join([*_keys, key])
                    if _key in lang:
                        new_value = lang[_key]
                        _line = " " * offset_left + f"'{key}' => '" + new_value.replace("'", "\\'") + "',"

            # value list
            elif line.endswith("'") or line.endswith("',") or line.endswith('"') or line.endswith('",'):
                continue  # delete value lines

            else:
                raise ValueError(f"WARN: Unhandled line: {line!r}")
            _lines.append(_line)

    return _lines


def dump_all():
    target_dir = Path("./en")
    lang = {}

    for child in target_dir.glob("**/*"):
        if not child.is_file():
            continue
        if child.suffix != ".php":
            print("WARN: not .php:", child)
            continue

        _file_key = ".".join(child.relative_to(target_dir).with_suffix("").parts)
        try:
            for key, value in load_from(child).items():
                lang[_file_key + "/" + key] = value
        except Exception:
            print("Error in", child)
            raise

    with open("pterodactyl_panel_lang_en.json", "w", encoding="utf8") as file:
        json.dump(lang, file, indent=2)


def apply_all(json_file):
    original_dir = Path("./en")
    write_dir = Path("./ja")
    lang_file = Path(json_file)

    with open(lang_file, "r", encoding="utf8") as f:
        lang = json.load(f)
    lang_file_keys = set(k.split("/")[0] for k in lang.keys())

    for child in original_dir.glob("**/*"):
        if not child.is_file():
            continue
        if child.suffix != ".php":
            print("WARN: not .php:", child)
            continue

        _file_key = ".".join(child.relative_to(original_dir).with_suffix("").parts)
        if _file_key not in lang_file_keys:
            continue

        try:
            k_pre = _file_key + "/"
            lines = load_to_remap_dump(child, {k[len(k_pre):]: v for k, v in lang.items() if k.startswith(k_pre)})

            (write_dir / child.relative_to(original_dir)).parent.mkdir(parents=True, exist_ok=True)
            with open(write_dir / child.relative_to(original_dir), "w", encoding="utf8") as f:
                f.write("\n".join(lines) + "\n")

        except Exception:
            print("Error in", child)
            raise


if __name__ == '__main__':
    try:
        mode = sys.argv[1]
    except IndexError:
        mode = None

    if mode == "json2ja":
        print("= Save mode = json -> ja")
        try:
            json_file_name = sys.argv[2]
        except IndexError:
            print("ERR:", "jsonファイル名を指定してください")
            sys.exit(1)
        apply_all(json_file_name)
    elif mode == "en2json":
        print("= Dump mode = en -> json")
        dump_all()
    else:
        print("mode を指定してください")
        print("  en2json         -> ./en pterodactyl_panel_lang_en.json に保存します")
        print("  json2ja (.json) -> ./en と json ファイルを読み取り、値を適用したファイルを ./ja に保存します")
        sys.exit(1)
