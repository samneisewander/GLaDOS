data = {
    "1": {
        "highscore": 3
    },
    "2": {
        "highscore": 4
    },
    "3": {
        "highscore": 5
    }
}

print(sorted(data.items(), key=lambda x: -x[1]['highscore']))