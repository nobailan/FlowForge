import csv

def main():
    with open('employees.csv', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    salaries = [int(r['salary']) for r in rows]
    avg_salary = sum(salaries) / len(salaries)

    highest = max(rows, key=lambda r: int(r['salary']))

    print(f"Average salary: {avg_salary:.2f}")
    print(f"Highest paid: {highest['name']} (${int(highest['salary']):,})")

if __name__ == '__main__':
    main()
