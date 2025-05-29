from neo4j import GraphDatabase

# Neo4j connection details
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "BDA123B00k!"

def get_users_in_large_communities():
    query = """
    // Find communities with more than one user
    MATCH (u:User)
    WITH u.community AS communityId, COLLECT(u) AS users, COUNT(u) AS size
    WHERE size > 1
    UNWIND users AS user
    RETURN user.id AS userId, user.location AS location, communityId
    ORDER BY communityId, userId
    """

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    with driver.session() as session:
        result = session.run(query)
        users = []
        for record in result:
            users.append({
                "userId": record["userId"],
                "location": record["location"],
                "communityId": record["communityId"],
            })
    driver.close()
    return users

# Example usage
# users = get_users_in_large_communities()
# print(f"Found {len(users)} users in communities with more than one user:")
# for u in users[:10]:  # print first 10
#     print(f'User {u["userId"]} in community {u["communityId"]} at location {u["location"]}')


def recommend_books_for_user(user_id):
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    query = """
        // Define the target user ID
        WITH $userId AS userId
        
        // Get the target user and their community ID
        MATCH (targetUser:User {id: userId})
        WITH targetUser, userId, targetUser.community AS communityId
        
        // Find other users in the same community (excluding the target user)
        MATCH (otherUser:User {community: communityId})
        WHERE otherUser.id <> userId
        
        // Get books positively rated (>= 6) by other users
        MATCH (otherUser)-[r:RATED]->(b:Book)
        WHERE r.rating >= 6
        
        // Exclude books already rated by the target user
          AND NOT (targetUser)-[:RATED]->(b)
        
        // Return recommended books with count of recommendations
        RETURN b.isbn AS recommendedBookISBN,
               b.title AS title,
               COUNT(*) AS recommendCount
        
        // Order by number of recommending users
        ORDER BY recommendCount DESC
        LIMIT 10
    """

    with driver.session() as session:
        result = session.run(query, userId=user_id)
        recommendations = []
        for record in result:
            recommendations.append({
                "ISBN": record["recommendedBookISBN"],
                "Title": record["title"],
                "RecommendCount": record["recommendCount"]
            })
    driver.close()
    return recommendations


# Example usage:
user_id = 61501  # test user's id here
recommended_books = recommend_books_for_user(user_id)
print("Recommended books:")
for book in recommended_books:
    print(f'{book["Title"]} (ISBN: {book["ISBN"]}) - recommended by {book["RecommendCount"]} users')
