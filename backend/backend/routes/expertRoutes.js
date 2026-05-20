const express = require("express");
const router = express.Router();
const mongoose = require("mongoose");

const ExpertSchema =
new mongoose.Schema({
    name: String,
    profession: String,
    experience: String,
    phone: String,
    email: String,
    languages: String
});

const Expert =
mongoose.model(
    "Expert",
    ExpertSchema
);

// Save Expert


router.post(
    "/",
    async (req, res) => {

        const expert =
        new Expert(req.body);

        await expert.save();

        res.json(expert);

    }
);

// Get Experts


router.get(
    "/",
    async (req, res) => {

        const experts =
        await Expert.find();

        res.json(experts);

    }
);

module.exports = router;