import numpy as np
import api.core.search_engine.utils as utils
import pandas as pd
import json


class RecommendationEngine:
    def __init__(self, SQL_Model=None, dataset_matrix=None):
        """
        Recommender object that uses point to plane projection method
        to rank several entries in the given Json file or Numpy Matrix
        :param Json_model: File containing labels and numerical values
        :param dataset_matrix: Alternative to a json model, you can instantiate an object with a Numpy Matrix.
        """
        # self.jfile = Json_model.json_dump
        jfile_list = [contractor.model_dump_json() for contractor in SQL_Model]
        pre_data = [json.loads(s) for s in jfile_list]
        pre_data = pd.DataFrame(pre_data)
        pre_data["name"] = pre_data["first_name"] + " " + pre_data["last_name"]
        self.all_labels = [col for col in pre_data.columns if col.endswith("_rating")]
        desired_columns = ["id", "name"] + self.all_labels
        self.arranged_data = pre_data[desired_columns]
        self.number_data = None

        # Assuming the top level of JSON is a dictionary, count its keys
        if SQL_Model is not None:
            self.D = len(self.all_labels)  # Dimension of each row.
            self.N = None

            try:
                self.N = self.arranged_data.shape[0]
                print("Number of entries:", self.N)
            except ValueError as e:
                print("An error occurred:", e)
            try:
                rating_df = self.arranged_data[self.all_labels]
                self.number_data = rating_df.to_numpy()
                self.__data_Z_score_norm()
                print("NumPy matrix:\n", self.number_data)
            except Exception as e:
                print(
                    "An error occurred when parsing the rating columns to numpy array:",
                    e,
                )
        else:
            print(dataset_matrix)
            self.number_data = np.array(dataset_matrix)
            self.N, self.D = self.number_data.shape
            # self.N = dataset_matrix.shape[0]
            # self.D = dataset_matrix.shape[1]
            # self.data = dataset_matrix
            self.__replace_nan_with_column_mean()
            self.__data_Z_score_norm()
        # self.number_data = np.random.rand(self.N, self.D)*5
        self.static_vector = np.zeros(self.D)
        self.dynamic_vector = np.zeros(self.D)
        self.normal_vector = np.zeros(self.D)

    def set_static_vector(self, importance_vector: dict):
        """
        Method to set default settings vector that will
        affect all projections/recommendations made
        independently of the change of dynamic/preferences
        vector.
        :param importance_vector: default_vector. Dictionary with rating labels and their corresponding values.
        :return: None
        """
        for label, value in importance_vector.items():
            if label in self.all_labels:
                index = self.all_labels.index(label)
                self.static_vector[index] = value

    def set_dynamic_vector(self, importance_vector: dict):
        """
        Method used to set or update the current user preferences over
        the dimensions of ratings. The user preferences vector length
        and the static (system default) preferences should add up to
        "D": the total number of dimmensions considered in the ranking
        process.
        :param importance_vector: Unscaled vector with
         importance given to each feature.
        """
        for label, value in importance_vector.items():
            if label in self.all_labels:
                index = self.all_labels.index(label)
                self.static_vector[index] = value

    def __update_normal_vector(self):
        """
        Method that updates the normal (to rec-plane) vector
        based on current dynamic and static vector values.
        The process merges vectors into one keeping the
        order of the object's all_labels. Then applies
        softmax function to keep operations correctly scaled.
        If static_vector is None, then the normal vector is
        equal to the dynamic vector.
        :return: None
        """

        merged_vector = self.static_vector + self.dynamic_vector
        # Apply softmax to the merged vector
        self.normal_vector = utils.softmax(merged_vector)
        normal_vector_magnitude = np.linalg.norm(self.normal_vector)
        self.normal_vector /= normal_vector_magnitude

    def __data_Z_score_norm(self):
        means = np.mean(self.number_data, axis=0)
        stds = np.std(self.number_data, axis=0)

        # Perform Z-score normalization
        self.number_data = (self.number_data - means) / stds

        # Handle the case where standard deviation is zero
        self.number_data[:, stds == 0] = 0

        return self.number_data

    def recommend(self, importance_vector=None) -> list[str]:
        """
        Use this method to produce a ranked list based on the
        preferences set to object. For custom user reccomendations
        make sure to execute set_dynamic_vector first.
        :return: list(str) Ranked-sorted list of contractor IDs
        """
        if importance_vector is not None:
            self.set_dynamic_vector(importance_vector)
        self.__update_normal_vector()
        projections = np.dot(self.number_data, self.normal_vector)
        ranking_indices = np.argsort(projections)
        ranking_indices = ranking_indices[::-1]

        id_numbers = self.arranged_data["id"][ranking_indices].to_list()

        return id_numbers

    def __replace_nan_with_column_mean(self):
        # Calculate the mean of each column, ignoring NaNs

        col_means = np.nanmean(self.number_data, axis=0)

        # Replace NaNs with the mean of their respective column
        for i, mean in enumerate(col_means):
            self.number_data[np.isnan(self.number_data[:, i]), i] = mean

    def data_col(self, col_number: int):
        return self.number_data[:, col_number]
