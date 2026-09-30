import { useCallback, useEffect, useState } from "react";

import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const emptyCustomer = { name: "", email: "", phone: "" };
const emptyLoan = {
    customer_id: "",
    principal: "",
    interest_rate: "",
    tenure_months: ""
};

const money = (value) =>
    "₹" + Number(value).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

// Turns FastAPI error bodies (string or validation list) into readable text
const errorMessage = (body, fallback) => {
    if (!body || !body.detail) return fallback;
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
        return body.detail
            .map((e) => `${(e.loc || []).slice(1).join(".")}: ${e.msg}`)
            .join("\n");
    }
    return fallback;
};

async function api(path, options) {
    let response;
    try {
        response = await fetch(`${API_URL}${path}`, options);
    } catch {
        throw new Error(
            "Cannot reach the server. Is the backend running on " + API_URL + "?"
        );
    }

    let body = null;
    try {
        body = await response.json();
    } catch {
        // response had no JSON body
    }

    if (!response.ok) {
        throw new Error(errorMessage(body, `Request failed (${response.status})`));
    }
    return body;
}

const jsonOptions = (method, payload) => ({
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
});


function App() {

    const [customers, setCustomers] = useState([]);
    const [loans, setLoans] = useState([]);
    const [customerForm, setCustomerForm] = useState(emptyCustomer);
    const [loanForm, setLoanForm] = useState(emptyLoan);
    const [notice, setNotice] = useState(null); // { type, text }

    const showError = (error) =>
        setNotice({ type: "error", text: error.message });

    const showSuccess = (text) => setNotice({ type: "success", text });

    const customerName = (id) =>
        customers.find((c) => c.id === id)?.name ?? `#${id}`;


    // -------------------------------------------------
    // LOAD DATA
    // -------------------------------------------------

    const fetchCustomers = useCallback(async () => {
        setCustomers(await api("/customers"));
    }, []);

    const fetchLoans = useCallback(async () => {
        setLoans(await api("/loans"));
    }, []);

    useEffect(() => {
        let cancelled = false;

        Promise.all([api("/customers"), api("/loans")])
            .then(([customerData, loanData]) => {
                if (cancelled) return;
                setCustomers(customerData);
                setLoans(loanData);
            })
            .catch((error) => {
                if (!cancelled) setNotice({ type: "error", text: error.message });
            });

        return () => {
            cancelled = true;
        };
    }, []);


    // -------------------------------------------------
    // CUSTOMERS
    // -------------------------------------------------

    const handleCustomerChange = (event) => {
        const { name, value } = event.target;
        setCustomerForm((form) => ({ ...form, [name]: value }));
    };

    const createCustomer = async (event) => {
        event.preventDefault();
        try {
            await api("/customers", jsonOptions("POST", customerForm));
            setCustomerForm(emptyCustomer);
            await fetchCustomers();
            showSuccess("Customer created successfully");
        } catch (error) {
            showError(error);
        }
    };

    const deleteCustomer = async (customer) => {
        if (!window.confirm(`Delete customer "${customer.name}"?`)) return;
        try {
            await api(`/customers/${customer.id}`, { method: "DELETE" });
            await fetchCustomers();
            showSuccess("Customer deleted successfully");
        } catch (error) {
            showError(error);
        }
    };


    // -------------------------------------------------
    // LOANS
    // -------------------------------------------------

    const handleLoanChange = (event) => {
        const { name, value } = event.target;
        setLoanForm((form) => ({ ...form, [name]: value }));
    };

    const createLoan = async (event) => {
        event.preventDefault();
        try {
            await api(
                "/loans",
                jsonOptions("POST", {
                    customer_id: Number(loanForm.customer_id),
                    principal: Number(loanForm.principal),
                    interest_rate: Number(loanForm.interest_rate),
                    tenure_months: Number(loanForm.tenure_months)
                })
            );
            setLoanForm(emptyLoan);
            await fetchLoans();
            showSuccess("Loan created successfully");
        } catch (error) {
            showError(error);
        }
    };


    // -------------------------------------------------
    // PAYMENTS
    // -------------------------------------------------

    const makePayment = async (loan) => {
        const input = window.prompt(
            `Enter payment amount (outstanding: ${money(loan.outstanding_amount)}):`,
            loan.emi
        );

        if (input === null || input.trim() === "") return;

        const amount = Number(input);
        if (!Number.isFinite(amount) || amount <= 0) {
            setNotice({
                type: "error",
                text: "Please enter a valid amount greater than zero"
            });
            return;
        }

        try {
            const data = await api(
                `/loans/${loan.id}/payments`,
                jsonOptions("POST", { amount })
            );
            await fetchLoans();
            showSuccess(
                `Payment successful. Remaining: ${money(data.remaining_amount)}`
            );
        } catch (error) {
            showError(error);
        }
    };


    return (

        <div className="container">

            <h1>Loan Management System</h1>

            {notice && (
                <div
                    className={`notice ${notice.type}`}
                    role="alert"
                    onClick={() => setNotice(null)}
                >
                    {notice.text}
                </div>
            )}


            <section>
                <h2>Add Customer</h2>

                <form onSubmit={createCustomer} className="form">
                    <input
                        name="name"
                        placeholder="Customer Name"
                        value={customerForm.name}
                        onChange={handleCustomerChange}
                        required
                    />
                    <input
                        name="email"
                        type="email"
                        placeholder="Email"
                        value={customerForm.email}
                        onChange={handleCustomerChange}
                        required
                    />
                    <input
                        name="phone"
                        placeholder="Phone"
                        value={customerForm.phone}
                        onChange={handleCustomerChange}
                        minLength={5}
                        required
                    />
                    <button type="submit">Add Customer</button>
                </form>
            </section>


            <section>
                <h2>Customers</h2>

                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Phone</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {customers.length === 0 && (
                            <tr>
                                <td colSpan="5">No customers yet</td>
                            </tr>
                        )}
                        {customers.map((customer) => (
                            <tr key={customer.id}>
                                <td>{customer.id}</td>
                                <td>{customer.name}</td>
                                <td>{customer.email}</td>
                                <td>{customer.phone}</td>
                                <td>
                                    <button
                                        className="danger"
                                        onClick={() => deleteCustomer(customer)}
                                    >
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </section>


            <section>
                <h2>Create Loan</h2>

                <form onSubmit={createLoan} className="form">
                    <select
                        name="customer_id"
                        value={loanForm.customer_id}
                        onChange={handleLoanChange}
                        required
                    >
                        <option value="">Select customer</option>
                        {customers.map((customer) => (
                            <option key={customer.id} value={customer.id}>
                                {customer.name} (#{customer.id})
                            </option>
                        ))}
                    </select>
                    <input
                        name="principal"
                        type="number"
                        min="0.01"
                        step="0.01"
                        placeholder="Loan Amount"
                        value={loanForm.principal}
                        onChange={handleLoanChange}
                        required
                    />
                    <input
                        name="interest_rate"
                        type="number"
                        min="0"
                        max="100"
                        step="0.01"
                        placeholder="Interest Rate % (per year)"
                        value={loanForm.interest_rate}
                        onChange={handleLoanChange}
                        required
                    />
                    <input
                        name="tenure_months"
                        type="number"
                        min="1"
                        max="600"
                        step="1"
                        placeholder="Tenure (months)"
                        value={loanForm.tenure_months}
                        onChange={handleLoanChange}
                        required
                    />
                    <button type="submit">Create Loan</button>
                </form>
            </section>


            <section>
                <h2>Loans</h2>

                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Customer</th>
                            <th>Principal</th>
                            <th>Interest</th>
                            <th>Tenure</th>
                            <th>EMI</th>
                            <th>Outstanding</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loans.length === 0 && (
                            <tr>
                                <td colSpan="9">No loans yet</td>
                            </tr>
                        )}
                        {loans.map((loan) => (
                            <tr key={loan.id}>
                                <td>{loan.id}</td>
                                <td>{customerName(loan.customer_id)}</td>
                                <td>{money(loan.principal)}</td>
                                <td>{loan.interest_rate}%</td>
                                <td>{loan.tenure_months} mo</td>
                                <td>{money(loan.emi)}</td>
                                <td>{money(loan.outstanding_amount)}</td>
                                <td>{loan.status}</td>
                                <td>
                                    <button
                                        disabled={loan.status === "CLOSED"}
                                        onClick={() => makePayment(loan)}
                                    >
                                        Make Payment
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </section>

        </div>
    );
}


export default App;
