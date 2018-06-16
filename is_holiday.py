#!/usr/bin/env python3

from datetime import date
import holidays


if __name__ == '__main__':
    us_holidays = holidays.UnitedStates()

    if date.today() in us_holidays:
        exit(0)

    exit(-1)

