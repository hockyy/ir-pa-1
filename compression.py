import array

import bitarray as bitarray
from bitarray.util import int2ba


class StandardPostings:
    """
    Class dengan static methods, untuk mengubah representasi postings list
    yang awalnya adalah List of integer, berubah menjadi sequence of bytes.
    Kita menggunakan Library array di Python.

    ASUMSI: postings_list untuk sebuah term MUAT di memori!

    Silakan pelajari:
        https://docs.python.org/3/library/array.html
    """

    @staticmethod
    def encode(postings_list):
        """
        Encode postings_list menjadi stream of bytes

        Parameters
        ----------
        postings_list: List[int]
            List of docIDs (postings)

        Returns
        -------
        bytes
            bytearray yang merepresentasikan urutan integer di postings_list
        """
        # Untuk yang standard, gunakan L untuk unsigned long, karena docID
        # tidak akan negatif. Dan kita asumsikan docID yang paling besar
        # cukup ditampung di representasi 4 byte unsigned.
        return array.array('L', postings_list).tobytes()

    @staticmethod
    def decode(encoded_postings_list):
        """
        Decodes postings_list dari sebuah stream of bytes

        Parameters
        ----------
        encoded_postings_list: bytes
            bytearray merepresentasikan encoded postings list sebagai keluaran
            dari static method encode di atas.

        Returns
        -------
        List[int]
            list of docIDs yang merupakan hasil decoding dari encoded_postings_list
        """
        decoded_postings_list = array.array('L')
        decoded_postings_list.frombytes(encoded_postings_list)
        return decoded_postings_list.tolist()


class VBEPostings:
    """
    Berbeda dengan StandardPostings, dimana untuk suatu postings list,
    yang disimpan di disk adalah sequence of integers asli dari postings
    list tersebut apa adanya.

    Pada VBEPostings, kali ini, yang disimpan adalah gap-nya, kecuali
    posting yang pertama. Barulah setelah itu di-encode dengan Variable-Byte
    Enconding algorithm ke bytestream.

    Contoh:
    postings list [34, 67, 89, 454] akan diubah dulu menjadi gap-based,
    yaitu [34, 33, 22, 365]. Barulah setelah itu di-encode dengan algoritma
    compression Variable-Byte Encoding, dan kemudian diubah ke bytesream.

    ASUMSI: postings_list untuk sebuah term MUAT di memori!

    """

    @staticmethod
    def vb_encode_number(number):
        """
        Encodes a number using Variable-Byte Encoding
        Lihat buku teks kita!
        """
        bytes = []
        while True:
            bytes.insert(0, number % 128) # prepend ke depan
            if number < 128:
                break
            number = number // 128
        bytes[-1] += 128 # bit awal pada byte terakhir diganti 1
        return array.array('B', bytes).tobytes()

    @staticmethod
    def vb_encode(list_of_numbers):
        """
        Melakukan encoding (tentunya dengan compression) terhadap
        list of numbers, dengan Variable-Byte Encoding
        """
        bytes = []
        for number in list_of_numbers:
            bytes.append(VBEPostings.vb_encode_number(number))
        return b"".join(bytes)

    @staticmethod
    def encode(postings_list):
        """
        Encode postings_list menjadi stream of bytes (dengan Variable-Byte
        Encoding). JANGAN LUPA diubah dulu ke gap-based list, sebelum
        di-encode dan diubah ke bytearray.

        Parameters
        ----------
        postings_list: List[int]
            List of docIDs (postings)

        Returns
        -------
        bytes
            bytearray yang merepresentasikan urutan integer di postings_list
        """
        if len(postings_list) == 0: return []

        gap_based_list = [postings_list[0]]
        for i in range(1, len(postings_list)):
            gap_based_list.append(postings_list[i] - postings_list[i - 1])
        # print(gap_based_list)
        return VBEPostings.vb_encode(gap_based_list)

    @staticmethod
    def vb_decode(encoded_bytestream):
        """
        Decoding sebuah bytestream yang sebelumnya di-encode dengan
        variable-byte encoding.
        """
        decoded_vb = []
        current = 0
        for i in encoded_bytestream:
          # print(hex(i))
          # print(bin(i).strip('0b').zfill(8))
          current <<= 7
          current += (i & (128 - 1))
          if i >> 7 == 1:
            decoded_vb.append(current)
            current = 0
        return decoded_vb

    @staticmethod
    def decode(encoded_postings_list):
        """
        Decodes postings_list dari sebuah stream of bytes. JANGAN LUPA
        bytestream yang di-decode dari encoded_postings_list masih berupa
        gap-based list.

        Parameters
        ----------
        encoded_postings_list: bytes
            bytearray merepresentasikan encoded postings list sebagai keluaran
            dari static method encode di atas.

        Returns
        -------
        List[int]
            list of docIDs yang merupakan hasil decoding dari encoded_postings_list
        """
        gap_based_list = VBEPostings.vb_decode(encoded_postings_list)
        # print(gap_based_list)
        for i in range(1, len(gap_based_list)):
            gap_based_list[i] += gap_based_list[i-1]
        return gap_based_list

class EliasGammaPostings:
    """
    Coding $\gamma$ untuk suatu bilangan bulat positif $k$ terdiri dari dua
    komponen, yaitu sektor dan body
    Untuk mengencode:
    - Cari nilai terbesar dari $N$, sehingga $2^N \leq X$, dengan kata lain,
    kita mencari Most significant bit dari $X$, kemudian kita akan melakukan
    encoding bilangan $N$ menggunakan unary coding, itu untuk bagian sectornya.
    Unary coding untuk suatu bilangan $N$ merupakan $N -1$ buah $0$ diikuti
    dengan satu buah bit $1$.
    - Bagian sisanya, yaitu $X - 2^N$, direpresentasikan dengan binary,
    yaitu bagian bodynya.
    - Memori untuk mendecode suatu bilangan $x$ menjadi
    $2\lfloor\log_2(x)\rfloor + 1$. Bila kita bandingkan tanpa kompresi,
    menyimpan suatu bilangan $x$ membutuhkan memori sebanyak $\log_2(MAX) + 1$
    untuk setiap bilangannya. Jadi, bila bilangan besarnya sedikit
    (atau untuk yang gapnya banyak pada postings list, kompresi ini cocok
    digunakan)
    """

    @staticmethod
    def eliasgamma_encode(list_of_numbers):
        """
        Melakukan encoding (tentunya dengan compression) terhadap
        list of numbers, dengan elias gamma encoding
        """
        bit_array = bitarray.bitarray()
        for number in list_of_numbers:
            tmp = number
            assert(number > 0)
            while tmp > 1:
                tmp >>= 1
                bit_array.append(0)
            bit_array.extend(int2ba(number))
        return bit_array.tobytes()

    @staticmethod
    def encode(postings_list):
        """
        Encode postings_list menjadi stream of bytes (dengan Elias Gamma).
        JANGAN LUPA diubah dulu ke gap-based list, sebelum
        di-encode dan diubah ke bytearray.

        Parameters
        ----------
        postings_list: List[int]
            List of docIDs (postings)

        Returns
        -------
        bytes
            bytearray yang merepresentasikan urutan integer di postings_list
        """
        if len(postings_list) == 0: return []

        gap_based_list = [postings_list[0]]
        for i in range(1, len(postings_list)):
            gap_based_list.append(postings_list[i] - postings_list[i - 1])

        return EliasGammaPostings.eliasgamma_encode(gap_based_list)

    @staticmethod
    def eliasgamma_decode(encoded_bytestream):
        """
        Decoding sebuah bytestream yang sebelumnya di-encode dengan
        elias gamma encoding.
        """
        bit_array = bitarray.bitarray(endian="big")
        bit_array.frombytes(encoded_bytestream)
        decoded_posting_list = []
        ptr = 0
        while True:
            cnt = 0
            while (ptr < len(bit_array)) and (bit_array[ptr] == 0):
                ptr += 1
                cnt += 1
            if ptr == len(bit_array): break
            current_int = 1
            while cnt:
                cnt -= 1
                ptr += 1
                current_int <<= 1
                current_int += bit_array[ptr]
            ptr += 1
            decoded_posting_list.append(current_int)
        return decoded_posting_list
    @staticmethod
    def decode(encoded_postings_list):
        """
        Decodes postings_list dari sebuah stream of bytes. JANGAN LUPA
        bytestream yang di-decode dari encoded_postings_list masih berupa
        gap-based list.

        Parameters
        ----------
        encoded_postings_list: bytes
            bytearray merepresentasikan encoded postings list sebagai keluaran
            dari static method encode di atas.

        Returns
        -------
        List[int]
            list of docIDs yang merupakan hasil decoding dari encoded_postings_list
        """
        gap_based_list = EliasGammaPostings.eliasgamma_decode(encoded_postings_list)
        # print(gap_based_list)
        for i in range(1, len(gap_based_list)):
            gap_based_list[i] += gap_based_list[i-1]
        return gap_based_list

if __name__ == '__main__':

    postings_list = [34, 67, 89, 454, 2345738]
    for Postings in [StandardPostings, VBEPostings, EliasGammaPostings]:
        print(Postings.__name__)
        encoded_postings_list = Postings.encode(postings_list)
        print("byte hasil encode: ", encoded_postings_list)
        print("ukuran encoded postings: ", len(encoded_postings_list), "bytes")
        decoded_posting_list = Postings.decode(encoded_postings_list)
        print("hasil decoding: ", decoded_posting_list)
        assert decoded_posting_list == postings_list, "hasil decoding tidak sama dengan postings original"
        print()
