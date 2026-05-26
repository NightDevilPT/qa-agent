// mathUtils.js - Math utility functions for testing

/**
 * Basic arithmetic operations
 */
function add(a, b) {
    return a + b;
}

function subtract(a, b) {
    return a - b;
}

function multiply(a, b) {
    return a * b;
}

function divide(a, b) {
    if (b === 0) {
        throw new Error("Division by zero is not allowed");
    }
    return a / b;
}

/**
 * Advanced math operations
 */
function power(base, exponent) {
    return Math.pow(base, exponent);
}

function squareRoot(number) {
    if (number < 0) {
        throw new Error("Cannot calculate square root of negative number");
    }
    return Math.sqrt(number);
}

function factorial(n) {
    if (n < 0) {
        throw new Error("Factorial is not defined for negative numbers");
    }
    if (n === 0 || n === 1) {
        return 1;
    }
    let result = 1;
    for (let i = 2; i <= n; i++) {
        result *= i;
    }
    return result;
}

function absoluteValue(number) {
    return Math.abs(number);
}

/**
 * Statistical operations
 */
function mean(numbers) {
    if (!Array.isArray(numbers) || numbers.length === 0) {
        throw new Error("Input must be a non-empty array");
    }
    const sum = numbers.reduce((acc, val) => acc + val, 0);
    return sum / numbers.length;
}

function median(numbers) {
    if (!Array.isArray(numbers) || numbers.length === 0) {
        throw new Error("Input must be a non-empty array");
    }
    const sorted = [...numbers].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    
    if (sorted.length % 2 === 0) {
        return (sorted[mid - 1] + sorted[mid]) / 2;
    }
    return sorted[mid];
}

function sum(numbers) {
    if (!Array.isArray(numbers)) {
        throw new Error("Input must be an array");
    }
    return numbers.reduce((acc, val) => acc + val, 0);
}

/**
 * Trigonometry operations
 */
function toRadians(degrees) {
    return degrees * (Math.PI / 180);
}

function toDegrees(radians) {
    return radians * (180 / Math.PI);
}

function calculateHypotenuse(a, b) {
    return Math.sqrt(a * a + b * b);
}

/**
 * Utility functions
 */
function isEven(number) {
    return number % 2 === 0;
}

function isPrime(n) {
    if (n <= 1) return false;
    if (n <= 3) return true;
    if (n % 2 === 0 || n % 3 === 0) return false;
    
    for (let i = 5; i * i <= n; i += 6) {
        if (n % i === 0 || n % (i + 2) === 0) return false;
    }
    return true;
}

function roundTo(number, decimalPlaces) {
    const factor = Math.pow(10, decimalPlaces);
    return Math.round(number * factor) / factor;
}

module.exports = {
    add,
    subtract,
    multiply,
    divide,
    power,
    squareRoot,
    factorial,
    absoluteValue,
    mean,
    median,
    sum,
    toRadians,
    toDegrees,
    calculateHypotenuse,
    isEven,
    isPrime,
    roundTo
};