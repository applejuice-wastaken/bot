def human_join_list(input_list: list, *, analyse_contents=False, end_join=" and "):
    if len(input_list) == 0:
        return ""
    elif len(input_list) == 1:
        return input_list[0]
    elif analyse_contents and end_join in input_list[-1]:
        return ", ".join(input_list)
    else:
        return end_join.join((", ".join(input_list[:-1]), input_list[-1]))
