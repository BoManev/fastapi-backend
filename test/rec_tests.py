import unittest
import numpy as np
from api.core.search_engine.projection_engine import RecommendationEngine

alternate_dataset = [[1, 2, 3, 4], [2, 2, 3, 4], [3, 3, 3, 4], [4, 4, 4, 4]]


class TestRecommendationEngine(unittest.TestCase):
    def test_z_score_normalization(self):
        # Test data
        x_data = np.random.rand(10)
        y_data = np.random.rand(10)
        z_data = np.random.rand(10)

        # Create the dataset and transpose it to get the correct shape
        dataset = np.array([x_data, y_data, z_data]).T

        # Initialize the recommender with the dataset
        recommender = RecommendationEngine(dataset_matrix=dataset)

        # Normalize the data using the recommender's method

        # Manually calculate the Z-Score normalization
        x_mean, x_std = x_data.mean(), x_data.std()
        y_mean, y_std = y_data.mean(), y_data.std()
        z_mean, z_std = z_data.mean(), z_data.std()

        x_normalized = (x_data - x_mean) / x_std
        y_normalized = (y_data - y_mean) / y_std
        z_normalized = (z_data - z_mean) / z_std

        # Combine the manually normalized data
        manual_normalized_data = np.vstack((x_normalized, y_normalized, z_normalized)).T

        # Retrieve the normalized data from the recommender
        recommender_normalized_data = recommender.data

        # Assert that the two normalized datasets are almost equal
        np.testing.assert_array_almost_equal(
            recommender_normalized_data, manual_normalized_data, decimal=6
        )

    # def test_reccomendation_function(self, recommender_normalized_data, manual_normalized_data):
    #     data_points = alternate_dataset
    #     recommender = RecommendationEngine(dataset_matrix=alternate_dataset)
    #     # ranking_ixs = recommender.recommend()
    #     normal_vector = np.random.rand(4)

    #     normal_vector_magnitude = np.linalg.norm(normal_vector)
    #     unit_vector = normal_vector / normal_vector_magnitude

    #     # Calculate the projections
    #     projections = np.dot(data_points, unit_vector)

    #     # Get the ranking based on the projections
    #     # The indices will give you the ranking from lowest projection to highest
    #     ranking_indices = np.argsort(projections)

    #     # If you want from highest to lowest, you can reverse the array
    #     ranking_indices = ranking_indices[::-1]
    #     np.testing.assert_array_almost_equal(recommender_normalized_data, manual_normalized_data, decimal=6)


# This allows the test to be run from the command line
if __name__ == "__main__":
    unittest.main()
