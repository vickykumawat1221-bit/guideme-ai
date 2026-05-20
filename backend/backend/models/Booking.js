const mongoose = require("mongoose");

const bookingSchema = new mongoose.Schema({
  name: String,
  email: String,
  expert: String,
  date: String,
  message: String
});

module.exports = mongoose.model(
  "Booking",
  bookingSchema
);