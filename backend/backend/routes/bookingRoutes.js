const express = require("express");
const router = express.Router();
const Booking = require("../models/Booking");

router.post("/", async (req, res) => {
  try {
    const booking = new Booking(req.body);
    await booking.save();

    res.json({
      message: "Booking Saved"
    });
  } catch (error) {
    res.status(500).json({
      error: error.message
    });
  }
});

router.get("/", async (req, res) => {
  const bookings = await Booking.find();
  res.json(bookings);
});

module.exports = router;