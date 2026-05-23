const express = require("express");
const router = express.Router();
const mongoose = require("mongoose");

// const ExpertSchema =
// new mongoose.Schema({
//     name: String,
//     profession: String,
//     experience: String,
//     phone: String,
//     email: String,
//     languages: String
// });


const expertSchema = new mongoose.Schema({
  name: String,
  profession: String,
  experience: String,
  phone: String,
  email: String,
  languages: String,
  rating: {
    type: Number,
    default: 0
  },
  reviews: [
    {
      userName: String,
      comment: String,
      stars: Number,
      date: {
        type: Date,
        default: Date.now
      }
    }
  ]
});





const Expert =
mongoose.model(
    "Expert",
    expertSchema
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

//new changes
router.post("/:id/review", async (req, res) => {
  try {
    const { userName, comment, stars } = req.body;

    const expert = await Expert.findById(req.params.id);

    expert.reviews.push({
      userName,
      comment,
      stars
    });

    const totalStars = expert.reviews.reduce(
      (sum, review) => sum + review.stars,
      0
    );

    expert.rating = totalStars / expert.reviews.length;

    await expert.save();

    res.json(expert);

  } catch (error) {
    res.status(500).json({
      error: error.message
    });
  }
});




module.exports = router;