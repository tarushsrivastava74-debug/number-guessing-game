import random

number = random.randint(1, 10)  # generates a random number between 1 and 10
guess = "none"  # initializes the guess variable

while guess != number:
    guess = int(input("Guess a number between 1 and 10: "))  # prompts the user to guess a number

    if guess < number:
        print("Too low! Try again.")  # informs the user that their guess is too low
    elif guess > number:
        print("Too high! Try again.")  # informs the user that their guess is too high
    else:
        print("Congratulations! You guessed the number.")  # informs the user that they guessed correctly
