import traceback


def print_result(res):
    print('\n--RESULT:-------------------')
    print("EXIT:CODE:", res.exit_code)
    print("OUTPUT:", res.output)

    if res.exc_info and res.exception:
        traceback.print_exception(*res.exc_info)
        # print(res.exception)
    # print traceback

    # print("DIR:", dir(res))
    # traceback.print_exc(res.exc_info)
    print('--/RESULT:-------------------')
