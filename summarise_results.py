import csv
import sys

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage: python summarise_results.py results.csv"
        sys.exit(0)

    filename = sys.argv[1]
    errors = []
    errors_file = csv.reader(open(filename, 'rb'))
    for (plaque_file, error) in errors_file:
        errors.append(int(error))

    chart_data = ",".join([str(x) for x in errors])

    average_error = float(sum(errors)) / len(errors)

    print "Average error", average_error

